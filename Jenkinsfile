#!/usr/bin/env groovy

pipeline {

    agent {
        docker {
            image 'lsstts/develop-env:b45'
            args "-u root --entrypoint=''"
        }
    }

    environment {
        XML_REPORT="jenkinsReport/report.xml"
        MODULE_NAME="lsst.ts.tunablelaser"
    }

    stages {
        stage ('Install Requirements') {
            steps {
                withEnv(["HOME=${env.WORKSPACE}"]) {
                    sh """
                        source /home/saluser/.setup.sh
                        pip install pyserial
                        cd /home/saluser/repos/ts_idl && git fetch && git checkout tickets/DM-23773
                        make_idl_files.py TunableLaser
                    """
                }
            }
        }

            
        stage ('Unit Tests and Coverage Analysis') {
            steps {
                withEnv(["HOME=${env.WORKSPACE}"]) {
                    sh """
                        source /home/saluser/.setup.sh
                        setup -kr .
                        pytest --cov-report html --cov=${env.MODULE_NAME} --junitxml=${env.XML_REPORT}
                    """
                }
            }
        }
    }

    post {
        always {
            withEnv(["HOME=${env.WORKSPACE}"]) {
                sh 'chown -R 1003:1003 ${HOME}/'
            }
            junit 'jenkinsReport/*.xml'
            publishHTML (target:[
                allowMissing: false,
                alwaysLinkToLastBuild: false,
                keepAll: true,
                reportDir: 'htmlcov',
                reportFiles: 'index.html',
                reportName: "Coverage Report"
            ])
        }

        cleanup {
            deleteDir()
        }
    }
}
