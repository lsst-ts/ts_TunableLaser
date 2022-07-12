#!/usr/bin/env groovy

pipeline {

    agent {
        docker {
            alwaysPull true
            image 'lsstts/develop-env:develop'
            args "-u root --entrypoint=''"
        }
    }

    environment {
        XML_REPORT="jenkinsReport/report.xml"
        MODULE_NAME="lsst.ts.tunablelaser"
        work_branches = "${GIT_BRANCH} ${CHANGE_BRANCH} develop"
        MT_CONFIG_MTCALSYS_DIR = "/home/saluser/repos/ts_config_mtcalsys"
        user_ci = credentials('lsst-io')
        LTD_USERNAME="${user_ci_USR}"
        LTD_PASSWORD="${user_ci_PSW}"
    }

    stages {
        stage ('Install Requirements') {
            steps {
                withEnv(["WHOME=${env.WORKSPACE}"]) {
                    sh """
                        source /home/saluser/.setup_dev.sh || echo loading env failed. Continuing...
                        cd /home/saluser/repos/ts_xml && /home/saluser/.checkout_repo.sh ${work_branches} && git pull
                        cd /home/saluser/repos/ts_salobj && /home/saluser/.checkout_repo.sh ${work_branches} && git pull
                        cd /home/saluser/repos/ts_sal && /home/saluser/.checkout_repo.sh ${work_branches} && git pull
                        cd /home/saluser/repos/ts_config_mtcalsys && /home/saluser/.checkout_repo.sh ${work_branches} && git pull
                        make_idl_files.py TunableLaser
                    """
                }
            }
        }

            
        stage ('Unit Tests and Coverage Analysis') {
            steps {
                withEnv(["WHOME=${env.WORKSPACE}"]) {
                    sh """
                        source /home/saluser/.setup_dev.sh || echo loading env failed. Continuing...
                        pip install .[dev]
                        pytest --cov-report html --cov=${env.MODULE_NAME} --junitxml=${env.XML_REPORT}
                    """
                }
            }
        }
        
        stage('Build and Upload Documentation') {
            steps {
                withEnv(["WHOME=${env.WORKSPACE}"]) {
                    sh """
                        source /home/saluser/.setup_dev.sh || echo loading env failed. Continuing...
                        pip install .[dev]
                        package-docs build
                        ltd upload --product ts-tunablelaser --git-ref ${GIT_BRANCH} --dir doc/_build/html
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
