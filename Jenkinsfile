#!/usr/bin/env groovy

pipeline {

    agent {
        // Use the docker to assign the Python version.
        docker {
            image 'python:3.6.2'
            args '-u root'
        }
    }

    environment {
        // Use the double quote instead of single quote
        // XML report path
        XML_REPORT="jenkinsReport/report.xml"
    }

    stages {
        stage ('Install Requirements') {
            steps {
                // When using the docker container, we need to change
                // the HOME path to WORKSPACE to have the authority
                // to install the packages.
                withEnv(["HOME=${env.WORKSPACE}"]) {
                    sh """
                        pip install --user -r requirements-dev.txt -e .
                    """
                }
            }
        }

        stage('Unit Tests with Coverage') {
            steps {
                // Direct the HOME to WORKSPACE for pip to get the
                // installed library.
                // 'PATH' can only be updated in a single shell block.
                // We can not update PATH in 'environment' block.
                // Pytest needs to export the junit report.
                withEnv(["HOME=${env.WORKSPACE}"]) {
                    sh """
                        export PATH=$PATH:${env.WORKSPACE}/.local/bin
                        pytest --cov-report html --cov=lsst.ts.laser --junitxml=${env.WORKSPACE}/${env.XML_REPORT} ${env.WORKSPACE}/tests
                    """
                }
            }
        }
    }

    post {
        always {
            // The path of xml needed by JUnit is relative to
            // the workspace.
            junit 'jenkinsReport/*.xml'

            // Publish the HTML report
            publishHTML (target: [
                allowMissing: false,
                alwaysLinkToLastBuild: false,
                keepAll: true,
                reportDir: 'htmlcov',
                reportFiles: 'index.html',
                reportName: "Coverage Report"
              ])
        }
	success {
		emailext(attachLog: true, body: '''"""<p>SUCCESSFUL: Job \'${env.JOB_NAME} [${env.BUILD_NUMBER}]\':</p>
            <p>Check console output at &QUOT;<a href=\'${env.BUILD_URL}\'>${env.JOB_NAME} [${env.BUILD_NUMBER}]</a>&QUOT;</p>"""''', recipientProviders: [developers()], subject: '"SUCCESSFUL: Job \'${env.JOB_NAME} [${env.BUILD_NUMBER}]\'"')
	}

        cleanup {
            // clean up the workspace
            deleteDir()
        }
    }
}
