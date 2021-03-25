#!/usr/bin/groovy
/* Copyright (C) 2019-2021 Intel Corporation
 * All rights reserved.
 *
 * This file is part of the DAOS Project. It is subject to the license terms
 * in the LICENSE file found in the top-level directory of this distribution
 * and at https://img.shields.io/badge/License-BSD--2--Clause--Patent-blue.svg.
 * No part of the DAOS Project, including this file, may be copied, modified,
 * propagated, or distributed except according to the terms contained in the
 * LICENSE file.
 */

// To use a test branch (i.e. PR) until it lands to master
// I.e. for testing library changes
@Library(value="pipeline-lib@bmurrell/move-functions-from-DAOS-Jenkinsfile") _

// For master, this is just some wildly high number
next_version = "1000"

// Don't define this as a type or it loses it's global scope
target_branch = env.CHANGE_TARGET ? env.CHANGE_TARGET : env.BRANCH_NAME
def sanitized_JOB_NAME = JOB_NAME.toLowerCase().replaceAll('/', '-').replaceAll('%2f', '-')

// bail out of branch builds that are not on a whitelist
if (!env.CHANGE_ID &&
    (!env.BRANCH_NAME.startsWith("weekly-testing") &&
     !env.BRANCH_NAME.startsWith("release/") &&
     env.BRANCH_NAME != "master")) {
   currentBuild.result = 'SUCCESS'
   return
}

// The docker agent setup and the provisionNodes step need to know the
// UID that the build agent is running under.
cached_uid = 0
def getuid() {
    if (cached_uid == 0)
        cached_uid = sh(label: 'getuid()',
                        script: "id -u",
                        returnStdout: true).trim()
    return cached_uid
}

// Default priority is 3, lower is better.
// The parameter for a job is set using the script/Jenkinsfile from the
// previous build of that job, so the first build of any PR will always
// run at default because Jenkins sees it as a new job, but subsequent
// ones will use the value from here.
// The advantage therefore is not to change the priority of PRs, but to
// change the master branch itself to run at lower priority, resulting
// in faster time-to-result for PRs.

String get_priority() {
    if (env.BRANCH_NAME == 'master' ||
        env.BRANCH_NAME.startsWith("release/") ||
        env.BRANCH_NAME == 'weekly-testing') {
        string p = '2'
    } else {
        string p = ''
    }
    echo "Build priority set to " + p == '' ? 'default' : p
    return p
}

boolean skip_prebuild() {
    return target_branch == 'weekly-testing'
}

boolean skip_checkpatch() {
    return skipStage(stage: 'checkpatch') ||
           docOnlyChange(target_branch) ||
           quickFunctional()
}

boolean skip_build() {
    // always build branch landings as we depend on lastSuccessfulBuild
    // always having RPMs in it
    return (env.BRANCH_NAME != target_branch) &&
           skipStage(stage: 'build') ||
           docOnlyChange(target_branch) ||
           rpmTestVersion() != ''
}

boolean skip_build_rpm(String distro) {
    return target_branch == 'weekly-testing' ||
           skipStage(stage: 'build-' + distro + '-rpm') ||
           distro == 'ubuntu20' && quickFunctional()
}

boolean skip_build_on_centos7_gcc() {
    return skipStage(stage: 'build-centos7-gcc') ||
           quickFunctional()
}

boolean skip_ftest(String distro) {
    return distro == 'ubuntu20' ||
           skipStage(stage: 'func-test') ||
           skipStage(stage: 'func-test-vm') ||
           ! testsInStage() ||
           skipStage(stage: 'func-test-' + distro)
}

boolean skip_test_rpms_centos7() {
    return target_branch == 'weekly-testing' ||
           skipStage(stage: 'test') ||
           skipStage(stage: 'test-centos-rpms') ||
           quickFunctional()
}

boolean skip_scan_rpms_centos7() {
    return target_branch == 'weekly-testing' ||
           skipStage(stage: 'scan-centos-rpms', def_val: true) ||
           quickFunctional()
}

boolean skip_ftest_hw(String size) {
    return env.DAOS_STACK_CI_HARDWARE_SKIP == 'true' ||
           skipStage(stage: 'func-test') ||
           skipStage(stage: 'func-hw-test') ||
           skipStage(stage: 'func-hw-test-' + size) ||
           ! testsInStage() ||
           (env.BRANCH_NAME == 'master' && ! startedByTimer())
}

boolean skip_bandit_check() {
    return cachedCommitPragma(pragma: 'Skip-python-bandit',
                              def_val: 'true') == 'true' ||
           quickFunctional()
}

boolean skip_build_on_centos7_bullseye() {
    return  env.NO_CI_TESTING == 'true' ||
            skipStage(stage: 'bullseye', def_val: true) ||
            quickFunctional()
}

boolean skip_build_on_centos7_gcc_debug() {
    return skipStage(stage: 'build-centos7-gcc-debug') ||
           quickBuild()
}

boolean skip_build_on_centos7_gcc_release() {
    return skipStage(stage: 'build-centos7-gcc-release') ||
           quickBuild()
}

boolean skip_build_on_centos8_gcc_dev() {
    return skipStage(stage: 'build-centos8-gcc-dev') ||
           quickBuild()
}

boolean skip_build_on_landing_branch() {
    return env.BRANCH_NAME != target_branch ||
           quickBuild()
}

boolean skip_build_on_ubuntu_clang() {
    return target_branch == 'weekly-testing' ||
           skipStage(stage: 'build-ubuntu-clang') ||
           quickBuild()

}

boolean skip_build_on_leap15_gcc() {
    return skipStage(stage: 'build-leap15-gcc') ||
            quickBuild()
}

boolean skip_build_on_leap15_icc() {
    return target_branch == 'weekly-testing' ||
           skipStage(stage: 'build-leap15-icc') ||
           quickBuild()
}

boolean skip_unit_testing_stage() {
    return  env.NO_CI_TESTING == 'true' ||
            (skipStage(stage: 'build') &&
             rpmTestVersion() == '') ||
            docOnlyChange(target_branch) ||
            skip_build_on_centos7_gcc() ||
            skipStage(stage: 'unit-tests')
}

boolean skip_coverity() {
    return skipStage(stage: 'coverity-test') ||
           quickFunctional() ||
           skipStage(stage: 'build')
}

boolean skip_if_unstable() {
    if (cachedCommitPragma(pragma: 'Allow-unstable-test') == 'true' ||
        env.BRANCH_NAME == 'master' ||
        env.BRANCH_NAME.startsWith("weekly-testing") ||
        env.BRANCH_NAME.startsWith("release/")) {
        return false
    }

    //Ok, it's a PR and the Allow pragma isn't set.  Skip if the build is
    //unstable.

    return currentBuild.currentResult == 'UNSTABLE'
}

boolean skip_testing_stage() {
    return  env.NO_CI_TESTING == 'true' ||
            (skipStage(stage: 'build') &&
             rpmTestVersion() == '') ||
            docOnlyChange(target_branch) ||
            skipStage(stage: 'test') ||
            (env.BRANCH_NAME.startsWith('weekly-testing') &&
             ! startedByTimer() &&
             ! startedByUser()) ||
            skip_if_unstable()
}

boolean skip_unit_test() {
    return skipStage(stage: 'unit-test') ||
           skipStage(stage: 'run_test')
}

boolean skip_bullseye_report() {
    return env.BULLSEYE == null ||
           skipStage(stage: 'bullseye', def_val: true)
}

// Reply with an empty string if quickBuild disabled to avoid discarding
// docker caches.
String quick_build_deps(String distro, always=false) {
    String rpmspec_args = ""
    if (!always) {
        if (!quickBuild() ) {
            return ""
        }
    }
    if (distro.startsWith('leap15')) {
        rpmspec_args = "--define dist\\ .suse.lp152 " +
                       "--undefine rhel " +
                       "--define suse_version\\ 1502"
    } else if (distro.startsWith('el7') || distro.startsWith('centos7')) {
        rpmspec_args = "--undefine suse_version " +
                       "--define rhel\\ 7"
    } else {
        error("Unknown distro: ${distro} in quick_build_deps()")
    }
    return sh(label: 'Get Quickbuild dependencies',
              script: "rpmspec -q " +
                      "--srpm " +
                      rpmspec_args + ' ' +
                      "--requires utils/rpms/daos.spec " +
                      "2>/dev/null",
              returnStdout: true)
}

pipeline {
    agent { label 'lightweight' }

    triggers {
        cron(env.BRANCH_NAME == 'master' ? 'TZ=America/Toronto\n0 0 * * *\n' : '' +
             env.BRANCH_NAME == 'release/1.2' ? 'TZ=America/Toronto\n0 12 * * *\n' : '' +
             env.BRANCH_NAME.startsWith('weekly-testing') ? 'H 0 * * 6' : '')
    }

    environment {
        BULLSEYE = credentials('bullseye_license_key')
        GITHUB_USER = credentials('daos-jenkins-review-posting')
        SSH_KEY_ARGS = "-ici_key"
        CLUSH_ARGS = "-o$SSH_KEY_ARGS"
        TEST_RPMS = cachedCommitPragma(pragma: 'RPM-test', def_val: 'true')
        SCONS_FAULTS_ARGS = sconsFaultsArgs()
    }

    options {
        // preserve stashes so that jobs can be started at the test stage
        preserveStashes(buildCount: 5)
        ansiColor('xterm')
        buildDiscarder(logRotator(artifactDaysToKeepStr: '100'))
    }

    parameters {
        string(name: 'BuildPriority',
               defaultValue: get_priority(),
               description: 'Priority of this build.  DO NOT USE WITHOUT PERMISSION.')
        string(name: 'TestTag',
               defaultValue: "daily_regression",
               description: 'Test-tag to use for this run')
    }

    stages {
        stage('Get Commit Message') {
            steps {
                script {
                    env.COMMIT_MESSAGE = sh(script: 'git show -s --format=%B',
                                            returnStdout: true).trim()
                }
            }
        }
        stage('Cancel Previous Builds') {
            when { changeRequest() }
            steps {
                cancelPreviousBuilds()
            }
        }
        stage('Pre-build') {
            when {
                beforeAgent true
                expression { ! skip_prebuild() }
            }
            parallel {
                stage('checkpatch') {
                    when {
                        beforeAgent true
                        expression { ! skip_checkpatch() }
                    }
                    agent {
                        dockerfile {
                            filename 'Dockerfile.checkpatch'
                            dir 'utils/docker'
                            label 'docker_runner'
                            additionalBuildArgs dockerBuildArgs(add_repos: false)
                        }
                    }
                    steps {
                        checkPatch user: GITHUB_USER_USR,
                                   password: GITHUB_USER_PSW,
                                   ignored_files: "src/control/vendor/*:" +
                                                  "src/include/daos/*.pb-c.h:" +
                                                  "src/common/*.pb-c.[ch]:" +
                                                  "src/mgmt/*.pb-c.[ch]:" +
                                                  "src/engine/*.pb-c.[ch]:" +
                                                  "src/security/*.pb-c.[ch]:" +
                                                  "src/client/java/daos-java/src/main/java/io/daos/dfs/uns/*:" +
                                                  "src/client/java/daos-java/src/main/java/io/daos/obj/attr/*:" +
                                                  "src/client/java/daos-java/src/main/native/include/daos_jni_common.h:" +
                                                  "src/client/java/daos-java/src/main/native/*.pb-c.[ch]:" +
                                                  "src/client/java/daos-java/src/main/native/include/*.pb-c.[ch]:" +
                                                  "*.crt:" +
                                                  "*.pem:" +
                                                  "*_test.go:" +
                                                  "src/cart/_structures_from_macros_.h:" +
                                                  "src/tests/ftest/*.patch:" +
                                                  "src/tests/ftest/large_stdout.txt"
                    }
                    post {
                        always {
                            archiveArtifacts artifacts: 'pylint.log', allowEmptyArchive: true
                            /* when JENKINS-39203 is resolved, can probably use stepResult
                               here and remove the remaining post conditions
                               stepResult name: env.STAGE_NAME,
                                          context: 'build/' + env.STAGE_NAME,
                                          result: ${currentBuild.currentResult}
                            */
                        }
                        /* temporarily moved into stepResult due to JENKINS-39203
                        success {
                            githubNotify credentialsId: 'daos-jenkins-commit-status',
                                         description: env.STAGE_NAME,
                                         context: 'pre-build/' + env.STAGE_NAME,
                                         status: 'SUCCESS'
                        }
                        unstable {
                            githubNotify credentialsId: 'daos-jenkins-commit-status',
                                         description: env.STAGE_NAME,
                                         context: 'pre-build/' + env.STAGE_NAME,
                                         status: 'FAILURE'
                        }
                        failure {
                            githubNotify credentialsId: 'daos-jenkins-commit-status',
                                         description: env.STAGE_NAME,
                                         context: 'pre-build/' + env.STAGE_NAME,
                                         status: 'ERROR'
                        }
                        */
                    }
                } // stage('checkpatch')
                stage('Python Bandit check') {
                    when {
                      beforeAgent true
                      expression { ! skip_bandit_check() }
                    }
                    agent {
                        dockerfile {
                            filename 'Dockerfile.code_scanning'
                            dir 'utils/docker'
                            label 'docker_runner'
                            additionalBuildArgs dockerBuildArgs()
                        }
                    }
                    steps {
                        pythonBanditCheck()
                    }
                    post {
                        always {
                            // Bandit will have empty results if it does not
                            // find any issues.
                            junit testResults: 'bandit.xml',
                                  allowEmptyResults: true
                        }
                    }
                } // stage('Python Bandit check')
            }
        }
        stage('Build') {
            /* Don't use failFast here as whilst it avoids using extra resources
             * and gives faster results for PRs it's also on for master where we
             * do want complete results in the case of partial failure
             */
            //failFast true
            when {
                beforeAgent true
                expression { ! skip_build() }
            }
            parallel {
                stage('Build RPM on CentOS 7') {
                    agent {
                        dockerfile {
                            filename 'Dockerfile.mockbuild'
                            dir 'utils/rpms/packaging'
                            label 'docker_runner'
                            additionalBuildArgs dockerBuildArgs()
                            args  '--group-add mock --cap-add=SYS_ADMIN --privileged=true'
                        }
                    }
                    steps {
                        buildRpm()
                    }
                    post {
                        success {
                            buildRpmPost condition: 'success'
                        }
                        unstable {
                            buildRpmPost condition: 'unstable'
                        }
                        failure {
                            buildRpmPost condition: 'failure'
                        }
                        unsuccessful {
                            buildRpmPost condition: 'unsuccessful'
                        }
                        cleanup {
                            buildRpmPost condition: 'cleanup'
                        }
                    }
                }
                stage('Build RPM on Leap 15') {
                    when {
                        beforeAgent true
                        expression { ! skip_build_rpm('leap15') }
                    }
                    agent {
                        dockerfile {
                            filename 'Dockerfile.mockbuild'
                            dir 'utils/rpms/packaging'
                            label 'docker_runner'
                            additionalBuildArgs dockerBuildArgs()
                            args  '--group-add mock --cap-add=SYS_ADMIN --privileged=true'
                        }
                    }
                    steps {
                        buildRpm()
                    }
                    post {
                        success {
                            buildRpmPost condition: 'success'
                        }
                        unstable {
                            buildRpmPost condition: 'unstable'
                        }
                        failure {
                            buildRpmPost condition: 'failure'
                        }
                        unsuccessful {
                            buildRpmPost condition: 'unsuccessful'
                        }
                        cleanup {
                            buildRpmPost condition: 'cleanup'
                        }
                    }
                }
                stage('Build DEB on Ubuntu 20.04') {
                    when {
                        beforeAgent true
                        expression { ! skip_build_rpm('ubuntu20') }
                    }
                    agent {
                        dockerfile {
                            filename 'Dockerfile.ubuntu.20.04'
                            dir 'utils/rpms/packaging'
                            label 'docker_runner'
                            args '--privileged=true'
                            additionalBuildArgs dockerBuildArgs()
                            args  '--cap-add=SYS_ADMIN --privileged=true'
                        }
                    }
                    steps {
                        buildRpm()
                    }
                    post {
                        success {
                            buildRpmPost condition: 'success'
                        }
                        unstable {
                            buildRpmPost condition: 'unstable'
                        }
                        failure {
                            buildRpmPost condition: 'failure'
                        }
                        unsuccessful {
                            buildRpmPost condition: 'unsuccessful'
                        }
                        cleanup {
                            buildRpmPost condition: 'cleanup'
                        }
                    }
                }
                stage('Build on CentOS 7') {
                    when {
                        beforeAgent true
                        expression { ! skip_build_on_centos7_gcc() }
                    }
                    agent {
                        dockerfile {
                            filename 'utils/docker/Dockerfile.centos.7'
                            label 'docker_runner'
                            additionalBuildArgs dockerBuildArgs(qb: quickBuild()) +
                                                " -t ${sanitized_JOB_NAME}-centos7 " +
                                                ' --build-arg QUICKBUILD_DEPS="' +
                                                quick_build_deps('centos7') + '"' +
                                                ' --build-arg REPOS="' + prRepos() + '"'
                        }
                    }
                    steps {
                        sconsBuild parallel_build: parallelBuild(),
                                   stash_files: 'ci/test_files_to_stash.txt',
                                   scons_exe: 'scons-3',
                                   scons_args: sconsFaultsArgs()
                    }
                    post {
                        always {
                            recordIssues enabledForFailure: true,
                                         aggregatingResults: true,
                                         tool: gcc4(pattern: 'centos7-gcc-build.log',
                                                    id: "analysis-gcc-centos7")
                        }
                        unsuccessful {
                            sh """if [ -f config.log ]; then
                                      mv config.log config.log-centos7-gcc
                                  fi"""
                            archiveArtifacts artifacts: 'config.log-centos7-gcc',
                                             allowEmptyArchive: true
                        }
                    }
                }
                stage('Build on CentOS 7 Bullseye') {
                    when {
                        beforeAgent true
                        expression { ! skip_build_on_centos7_bullseye() }
                    }
                    agent {
                        dockerfile {
                            filename 'utils/docker/Dockerfile.centos.7'
                            label 'docker_runner'
                            additionalBuildArgs dockerBuildArgs(qb: quickBuild()) +
                                " -t ${sanitized_JOB_NAME}-centos7 " +
                                ' --build-arg BULLSEYE=' + env.BULLSEYE +
                                ' --build-arg QUICKBUILD_DEPS="' +
                                quick_build_deps('centos7') + '"' +
                                ' --build-arg REPOS="' + prRepos() + '"'
                        }
                    }
                    steps {
                        sconsBuild parallel_build: parallelBuild(),
                                   stash_files: 'ci/test_files_to_stash.txt',
                                   scons_exe: 'scons-3',
                                   scons_args: sconsFaultsArgs()
                    }
                    post {
                        always {
                            recordIssues enabledForFailure: true,
                                         aggregatingResults: true,
                                         tool: gcc4(pattern: 'centos7-covc-build.log',
                                                    id: "analysis-covc-centos7")
                        }
                        unsuccessful {
                            sh """if [ -f config.log ]; then
                                      mv config.log config.log-centos7-covc
                                  fi"""
                            archiveArtifacts artifacts: 'config.log-centos7-covc',
                                             allowEmptyArchive: true
                        }
                    }
                }
                stage('Build on CentOS 7 debug') {
                    when {
                        beforeAgent true
                        expression { ! skip_build_on_centos7_gcc_debug() }
                    }
                    agent {
                        dockerfile {
                            filename 'utils/docker/Dockerfile.centos.7'
                            label 'docker_runner'
                            additionalBuildArgs dockerBuildArgs(qb: quickBuild(),
                                                                deps_build: true) +
                                                " -t ${sanitized_JOB_NAME}-centos7 " +
                                                ' --build-arg QUICKBUILD_DEPS="' +
                                                quick_build_deps('centos7') + '"' +
                                                ' --build-arg REPOS="' + prRepos() + '"'
                        }
                    }
                    steps {
                        sconsBuild parallel_build: parallelBuild(),
                                   scons_exe: 'scons-3',
                                   scons_args: "PREFIX=/opt/daos TARGET_TYPE=release",
                                   build_deps: "no"
                    }
                    post {
                        always {
                            recordIssues enabledForFailure: true,
                                         aggregatingResults: true,
                                         tool: gcc4(pattern: 'centos7-gcc-debug-build.log',
                                                    id: "analysis-gcc-centos7-debug")
                        }
                        unsuccessful {
                            sh """if [ -f config.log ]; then
                                      mv config.log config.log-centos7-gcc-debug
                                  fi"""
                            archiveArtifacts artifacts: 'config.log-centos7-gcc-debug',
                                             allowEmptyArchive: true
                        }
                    }
                }
                stage('Build on CentOS 7 release') {
                    when {
                        beforeAgent true
                        expression { ! skip_build_on_centos7_gcc_release() }
                    }
                    agent {
                        dockerfile {
                            filename 'utils/docker/Dockerfile.centos.7'
                            label 'docker_runner'
                            additionalBuildArgs dockerBuildArgs(qb: quickBuild(),
                                                                deps_build: true) +
                                                " -t ${sanitized_JOB_NAME}-centos7 " +
                                                ' --build-arg QUICKBUILD_DEPS="' +
                                                quick_build_deps('centos7') + '"' +
                                                ' --build-arg REPOS="' + prRepos() + '"'
                        }
                    }
                    steps {
                        sconsBuild parallel_build: parallelBuild(),
                                   scons_exe: 'scons-3',
                                   scons_args: "PREFIX=/opt/daos TARGET_TYPE=release",
                                   build_deps: "no"
                    }
                    post {
                        always {
                            recordIssues enabledForFailure: true,
                                         aggregatingResults: true,
                                         tool: gcc4(pattern: 'centos7-gcc-release-build.log',
                                                    id: "analysis-gcc-centos7-release")
                        }
                        unsuccessful {
                            sh """if [ -f config.log ]; then
                                      mv config.log config.log-centos7-gcc-release
                                  fi"""
                            archiveArtifacts artifacts: 'config.log-centos7-gcc-release',
                                             allowEmptyArchive: true
                        }
                    }
                }
                stage('Build on CentOS 7 with Clang') {
                    when {
                        beforeAgent true
                        expression { ! skip_build_on_landing_branch() }
                    }
                    agent {
                        dockerfile {
                            filename 'utils/docker/Dockerfile.centos.7'
                            label 'docker_runner'
                            additionalBuildArgs dockerBuildArgs(qb: quickBuild(),
                                                                deps_build: true) +
                                                " -t ${sanitized_JOB_NAME}-centos7 " +
                                                ' --build-arg QUICKBUILD_DEPS="' +
                                                quick_build_deps('centos7') + '"'
                        }
                    }
                    steps {
                        sconsBuild parallel_build: parallelBuild(),
                                   scons_exe: 'scons-3',
                                   scons_args: sconsFaultsArgs() + " PREFIX=/opt/daos TARGET_TYPE=release",
                                   build_deps: "no"
                    }
                    post {
                        always {
                            recordIssues enabledForFailure: true,
                                         aggregatingResults: true,
                                         tool: clang(pattern: 'centos7-clang-build.log',
                                                     id: "analysis-centos7-clang")
                        }
                        unsuccessful {
                            sh """if [ -f config.log ]; then
                                      mv config.log config.log-centos7-clang
                                  fi"""
                            archiveArtifacts artifacts: 'config.log-centos7-clang',
                                             allowEmptyArchive: true
                        }
                    }
                }
                stage('Build on CentOS 8') {
                    when {
                        beforeAgent true
                        expression { ! skip_build_on_centos8_gcc_dev() }
                     }
                    agent {
                        dockerfile {
                            filename 'utils/docker/Dockerfile.centos.8'
                            label 'docker_runner'
                            additionalBuildArgs dockerBuildArgs(qb: quickBuild(),
                                                                deps_build: true) +
                                                " -t ${sanitized_JOB_NAME}-centos8 "
                        }
                    }
                    steps {
                        sconsBuild parallel_build: parallelBuild(),
                                   scons_args: sconsFaultsArgs() + " PREFIX=/opt/daos TARGET_TYPE=release",
                                   build_deps: "no",
                                   scons_exe: 'scons-3'
                    }
                    post {
                        always {
                            recordIssues enabledForFailure: true,
                                         aggregatingResults: true,
                                         tool: gcc4(pattern: 'centos8-gcc-build.log',
                                                    id: "analysis-centos8-gcc")
                        }
                        unsuccessful {
                            sh """if [ -f config.log ]; then
                                      mv config.log config.log-centos8-gcc
                                  fi"""
                            archiveArtifacts artifacts: 'config.log-centos8-gcc',
                                             allowEmptyArchive: true
                        }
                    }
                }
                stage('Build on Ubuntu 20.04') {
                    when {
                        beforeAgent true
                        expression { ! skip_build_on_landing_branch() }
                    }
                    agent {
                        dockerfile {
                            filename 'utils/docker/Dockerfile.ubuntu.20.04'
                            label 'docker_runner'
                            additionalBuildArgs dockerBuildArgs(deps_build: true) +
                                                " -t ${sanitized_JOB_NAME}-ubuntu20.04"
                        }
                    }
                    steps {
                        sconsBuild parallel_build: parallelBuild(),
                                   scons_args: sconsFaultsArgs() + " PREFIX=/opt/daos TARGET_TYPE=release",
                                   build_deps: "no"
                    }
                    post {
                        always {
                            recordIssues enabledForFailure: true,
                                         aggregatingResults: true,
                                         tool: gcc4(pattern: 'ubuntu20.04-gcc-build.log',
                                                    id: "analysis-ubuntu20")
                        }
                        unsuccessful {
                            sh """if [ -f config.log ]; then
                                      mv config.log config.log-ubuntu20.04-gcc
                                  fi"""
                            archiveArtifacts artifacts: 'config.log-ubuntu20.04-gcc',
                                             allowEmptyArchive: true
                        }
                    }
                }
                stage('Build on Ubuntu 20.04 with Clang') {
                    when {
                        beforeAgent true
                        expression { ! skip_build_on_ubuntu_clang() }
                    }
                    agent {
                        dockerfile {
                            filename 'utils/docker/Dockerfile.ubuntu.20.04'
                            label 'docker_runner'
                            additionalBuildArgs dockerBuildArgs(deps_build: true) +
                                                " -t ${sanitized_JOB_NAME}-ubuntu20.04"
                        }
                    }
                    steps {
                        sconsBuild parallel_build: parallelBuild(),
                                   scons_args: sconsFaultsArgs() + " PREFIX=/opt/daos TARGET_TYPE=release",
                                   build_deps: "no"
                    }
                    post {
                        always {
                            recordIssues enabledForFailure: true,
                                         aggregatingResults: true,
                                         tool: clang(pattern: 'ubuntu20.04-clang-build.log',
                                                     id: "analysis-ubuntu20-clang")
                        }
                        unsuccessful {
                            sh """if [ -f config.log ]; then
                                      mv config.log config.log-ubuntu20.04-clang
                                  fi"""
                            archiveArtifacts artifacts: 'config.log-ubuntu20.04-clang',
                                             allowEmptyArchive: true
                        }
                    }
                }
                stage('Build on Leap 15') {
                    when {
                        beforeAgent true
                        expression { ! skip_build_on_leap15_gcc() }
                    }
                    agent {
                        dockerfile {
                            filename 'utils/docker/Dockerfile.leap.15'
                            label 'docker_runner'
                            additionalBuildArgs dockerBuildArgs(qb: quickBuild()) +
                                                " -t ${sanitized_JOB_NAME}-leap15 " +
                                                ' --build-arg QUICKBUILD_DEPS="' +
                                                quick_build_deps('leap15') + '"' +
                                                ' --build-arg REPOS="' + prRepos() + '"'
                        }
                    }
                    steps {
                        sconsBuild parallel_build: parallelBuild(),
                                   stash_files: 'ci/test_files_to_stash.txt',
                                   scons_args: sconsFaultsArgs()
                    }
                    post {
                        always {
                            recordIssues enabledForFailure: true,
                                         aggregatingResults: true,
                                         tool: gcc4(pattern: 'leap15-gcc-build.log',
                                                    id: "analysis-gcc-leap15")
                        }
                        unsuccessful {
                            sh """if [ -f config.log ]; then
                                      mv config.log config.log-leap15-gcc
                                  fi"""
                            archiveArtifacts artifacts: 'config.log-leap15-gcc',
                                             allowEmptyArchive: true
                        }
                    }
                }
                stage('Build on Leap 15 with Clang') {
                    when {
                        beforeAgent true
                        expression { ! skip_build_on_landing_branch() }
                    }
                    agent {
                        dockerfile {
                            filename 'utils/docker/Dockerfile.leap.15'
                            label 'docker_runner'
                            additionalBuildArgs dockerBuildArgs(deps_build: true) +
                                                " -t ${sanitized_JOB_NAME}-leap15"
                        }
                    }
                    steps {
                        sconsBuild parallel_build: parallelBuild(),
                                   scons_args: sconsFaultsArgs() + " PREFIX=/opt/daos TARGET_TYPE=release",
                                   build_deps: "no"
                    }
                    post {
                        always {
                            recordIssues enabledForFailure: true,
                                         aggregatingResults: true,
                                         tool: clang(pattern: 'leap15-clang-build.log',
                                                     id: "analysis-leap15-clang")
                        }
                        unsuccessful {
                            sh """if [ -f config.log ]; then
                                      mv config.log config.log-leap15-clang
                                  fi"""
                            archiveArtifacts artifacts: 'config.log-leap15-clang',
                                             allowEmptyArchive: true
                        }
                    }
                }
                stage('Build on Leap 15 with Intel-C and TARGET_PREFIX') {
                    when {
                        beforeAgent true
                        expression { ! skip_build_on_leap15_icc() }
                    }
                    agent {
                        dockerfile {
                            filename 'utils/docker/Dockerfile.leap.15'
                            label 'docker_runner'
                            additionalBuildArgs dockerBuildArgs(deps_build: true) +
                                                " -t ${sanitized_JOB_NAME}-leap15"
                            args '-v /opt/intel:/opt/intel'
                        }
                    }
                    steps {
                        sconsBuild parallel_build: parallelBuild(),
                                   scons_args: sconsFaultsArgs() + " PREFIX=/opt/daos TARGET_TYPE=release",
                                   build_deps: "no"
                    }
                    post {
                        always {
                            recordIssues enabledForFailure: true,
                                         aggregatingResults: true,
                                         tool: intel(pattern: 'leap15-icc-build.log',
                                                     id: "analysis-leap15-intelc")
                        }
                        unsuccessful {
                            sh """if [ -f config.log ]; then
                                      mv config.log config.log-leap15-intelc
                                  fi"""
                            archiveArtifacts artifacts: 'config.log-leap15-intelc',
                                             allowEmptyArchive: true
                        }
                    }
                }
            }
        }
        stage('Unit Tests') {
            when {
                beforeAgent true
                expression { ! skip_unit_testing_stage() }
            }
            parallel {
                stage('Unit Test') {
                    when {
                      beforeAgent true
                      expression { ! skip_unit_test() }
                    }
                    agent {
                        label 'ci_vm1'
                    }
                    steps {
                        unitTest timeout_time: 60,
                                 inst_repos: prRepos(),
                                 inst_rpms: unitPackages()
                    }
                    post {
                      always {
                            unitTestPost artifacts: ['unit_test_logs/*']
                        }
                    }
                }
                stage('NLT') {
                    when {
                      beforeAgent true
                      expression { ! skipStage(stage: 'nlt') }
                    }
                    agent {
                        label 'ci_nlt_1'
                    }
                    steps {
                        unitTest timeout_time: 30,
                                 inst_repos: prRepos(),
                                 test_script: 'ci/unit/test_nlt.sh',
                                 inst_rpms: unitPackages()
                    }
                    post {
                      always {
                            unitTestPost artifacts: ['nlt_logs/*'],
                                         testResults: 'None',
                                         always_script: 'ci/unit/test_nlt_post.sh',
                                         valgrind_stash: 'centos7-gcc-nlt-memcheck'
                            recordIssues enabledForFailure: true,
                                         failOnError: false,
                                         ignoreFailedBuilds: false,
                                         ignoreQualityGate: true,
                                         name: "NLT server leaks",
                                         tool: issues(pattern: 'nlt-server-leaks.json',
                                           name: 'NLT server results',
                                           id: 'NLT_server')
                            recordIssues enabledForFailure: true,
                                         failOnError: false,
                                         ignoreFailedBuilds: false,
                                         ignoreQualityGate: true,
                                         name: "NLT client leaks",
                                         tool: issues(pattern: 'nlt-client-leaks.json',
                                           name: 'NLT client results',
                                           id: 'NLT_client')
                        }
                    }
                }
                stage('Unit Test Bullseye') {
                    when {
                      beforeAgent true
                      expression { ! skipStage(stage: 'bullseye', def_val: true) }
                    }
                    agent {
                        label 'ci_vm1'
                    }
                    steps {
                        unitTest timeout_time: 60,
                                 ignore_failure: true,
                                 inst_repos: prRepos(),
                                 inst_rpms: unitPackages()
                    }
                    post {
                        always {
                            // This is only set while dealing with issues
                            // caused by code coverage instrumentation affecting
                            // test results, and while code coverage is being
                            // added.
                            unitTestPost ignore_failure: true,
                                         artifacts: ['covc_test_logs/*',
                                                     'covc_vm_test/**']
                        }
                    }
                } // stage('Unit test Bullseye')
                stage('Unit Test with memcheck') {
                    when {
                      beforeAgent true
                      expression { ! skipStage(stage: 'unit-test-memcheck') }
                    }
                    agent {
                        label 'ci_vm1'
                    }
                    steps {
                        unitTest timeout_time: 30,
                                 ignore_failure: true,
                                 inst_repos: prRepos(),
                                 inst_rpms: unitPackages()
                    }
                    post {
                        always {
                            unitTestPost artifacts: ['unit_test_memcheck_logs.tar.gz',
                                                     'unit_test_memcheck_logs/*.log'],
                                         valgrind_stash: 'centos7-gcc-unit-memcheck'
                        }
                    }
                } // stage('Unit Test with memcheck')
            }
        }
        stage('Test') {
            when {
                beforeAgent true
                expression { ! skip_testing_stage() }
            }
            parallel {
                stage('Coverity on CentOS 7') {
                    when {
                        beforeAgent true
                        expression { ! skip_coverity() }
                    }
                    agent {
                        dockerfile {
                            filename 'utils/docker/Dockerfile.centos.7'
                            label 'docker_runner'
                            additionalBuildArgs dockerBuildArgs(qb: true) +
                                                " -t ${sanitized_JOB_NAME}-centos7 " +
                                                ' --build-arg QUICKBUILD_DEPS="' +
                                                quick_build_deps('centos7', true) + '"' +
                                                ' --build-arg REPOS="' + prRepos() + '"'
                        }
                    }
                    steps {
                        sconsBuild coverity: "daos-stack/daos",
                                   parallel_build: parallelBuild(),
                                   scons_exe: 'scons-3'
                    }
                    post {
                        success {
                            coverityPost condition: 'success'
                        }
                        unsuccessful {
                            coverityPost condition: 'unsuccessful'
                        }
                    }
                } // stage('Coverity on CentOS 7')
                stage('Functional on CentOS 7') {
                    when {
                        beforeAgent true
                        expression { ! skip_ftest('el7') }
                    }
                    agent {
                        label 'stage_vm9'
                    }
                    steps {
                        functionalTest inst_repos: daosRepos(),
                                       inst_rpms: functionalPackages(1, next_version),
                                       test_function: 'runTestFunctionalV2'
                    }
                    post {
                        always {
                            functionalTestPostV2()
                        }
                    }
                } // stage('Functional on CentOS 7')
                stage('Functional on Leap 15') {
                    when {
                        beforeAgent true
                        expression { ! skip_ftest('leap15') }
                    }
                    agent {
                        label 'stage_vm9'
                    }
                    steps {
                        functionalTest inst_repos: daosRepos(),
                                       inst_rpms: functionalPackages(1, next_version),
                                       test_function: 'runTestFunctionalV2'
                    }
                    post {
                        always {
                            functionalTestPostV2()
                        }
                    } // post
                } // stage('Functional on Leap 15')
                stage('Functional on Ubuntu 20.04') {
                    when {
                        beforeAgent true
                        expression { ! skip_ftest('ubuntu20') }
                    }
                    agent {
                        label 'ci_vm9'
                    }
                    steps {
                        functionalTest inst_repos: daosRepos(),
                                       inst_rpms: functionalPackages(1, next_version),
                                       test_function: 'runTestFunctionalV2'
                    }
                    post {
                        always {
                            functionalTestPostV2()
                        }
                    } // post
                } // stage('Functional on Ubuntu 20.04')
                stage('Test CentOS 7 RPMs') {
                    when {
                        beforeAgent true
                        expression { ! skip_test_rpms_centos7() }
                    }
                    agent {
                        label 'ci_vm1'
                    }
                    steps {
                        testRpm inst_repos: daosRepos(),
                                daos_pkg_version: daos_packages_version()
                   }
                } // stage('Test CentOS 7 RPMs')
                stage('Scan CentOS 7 RPMs') {
                    when {
                        beforeAgent true
                        expression { ! skip_scan_rpms_centos7() }
                    }
                    agent {
                        label 'ci_vm1'
                    }
                    steps {
                        scanRpms inst_repos: daosRepos(),
                                 daos_pkg_version: daos_packages_version(),
                                 inst_rpms: 'clamav clamav-devel',
                                 test_script: 'ci/rpm/scan_daos.sh',
                                 junit_files: 'maldetect.xml'
                    }
                    post {
                        always {
                            junit 'maldetect.xml'
                        }
                    }
                } // stage('Scan CentOS 7 RPMs')
            } // parallel
        } // stage('Test')
        stage('Test Hardware') {
            when {
                beforeAgent true
                expression { ! skip_testing_stage() }
            }
            parallel {
                stage('Functional_Hardware_Small') {
                    when {
                        beforeAgent true
                        expression { ! skip_ftest_hw('small') }
                    }
                    agent {
                        // 2 node cluster with 1 IB/node + 1 test control node
                        label 'stage_nvme3'
                    }
                    steps {
                        functionalTest inst_repos: daosRepos(),
                                       inst_rpms: functionalPackages(1, next_version),
                                       test_function: 'runTestFunctionalV2'
                    }
                    post {
                        always {
                            functionalTestPostV2()
                        }
                    }
                } // stage('Functional_Hardware_Small')
                stage('Functional_Hardware_Medium') {
                    when {
                        beforeAgent true
                        expression { ! skip_ftest_hw('medium') }
                    }
                    agent {
                        // 4 node cluster with 2 IB/node + 1 test control node
                        label 'ci_nvme5'
                    }
                    steps {
                        functionalTest target: hwDistroTarget(),
                                       inst_repos: daosRepos(),
                                       inst_rpms: functionalPackages(1, next_version),
                                       test_function: 'runTestFunctionalV2'
                   }
                    post {
                        always {
                            functionalTestPostV2()
                        }
                    }
                } // stage('Functional_Hardware_Medium')
                stage('Functional_Hardware_Large') {
                    when {
                        beforeAgent true
                        expression { ! skip_ftest_hw('large') }
                    }
                    agent {
                        // 8+ node cluster with 1 IB/node + 1 test control node
                        label 'ci_nvme9'
                    }
                    steps {
                        functionalTest target: hwDistroTarget(),
                                       inst_repos: daosRepos(),
                                       inst_rpms: functionalPackages(1, next_version),
                                       test_function: 'runTestFunctionalV2'
                    }
                    post {
                        always {
                            functionalTestPostV2()
                        }
                    }
                } // stage('Functional_Hardware_Large')
            } // parallel
        } // stage('Test Hardware')
        stage ('Test Report') {
            parallel {
                stage('Bullseye Report') {
                    when {
                      beforeAgent true
                      expression { ! skip_bullseye_report() }
                    }
                    agent {
                        dockerfile {
                            filename 'utils/docker/Dockerfile.centos.7'
                            label 'docker_runner'
                            additionalBuildArgs dockerBuildArgs(qb: quickBuild()) +
                                " -t ${sanitized_JOB_NAME}-centos7 " +
                                ' --build-arg BULLSEYE=' + env.BULLSEYE +
                                ' --build-arg QUICKBUILD_DEPS="' +
                                quick_build_deps('centos7') + '"' +
                                ' --build-arg REPOS="' + prRepos() + '"'
                        }
                    }
                    steps {
                        // The coverage_healthy is primarily set here
                        // while the code coverage feature is being implemented.
                        cloverReportPublish coverage_stashes: ['centos7-covc-unit-cov'],
                                            coverage_healthy: [methodCoverage: 0,
                                                               conditionalCoverage: 0,
                                                               statementCoverage: 0],
                                            ignore_failure: true
                    }
                } // stage('Bullseye Report')
            } // parallel
        } // stage ('Test Report')
    } // stages
    post {
        always {
            valgrindReportPublish valgrind_stashes: ['centos7-gcc-nlt-memcheck',
                                                     'centos7-gcc-unit-memcheck']
        }
        unsuccessful {
            notifyBrokenBranch branches: target_branch
        }
    } // post
}
