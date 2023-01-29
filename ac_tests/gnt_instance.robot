*** Settings ***
Library    Process
Library    OperatingSystem
Library    SSHLibrary
Library    String
Suite Setup    Suite Setup
#Suite Teardown    Suite Teardown
Test Setup    Test Setup
#Test Teardown    Test Teardown

*** Variables ***
${INVENTORY}    inventory
${INVENTORY_ABSOLUE_PATH}    ac_tests/${INVENTORY}
${PLAYBOOK_INSTANCE}    pk_instance.yml

*** Test Cases ***
Test
    Run Ansible Playbook    ${PLAYBOOK_INSTANCE}    inventory=${INVENTORY}


*** Keywords ***
Suite Setup
    Run Vagrant And Get VM IP
    Create inventory

Suite Teardown
    Remove inventory
    #Run Process    vagrant destroy --force    shell=True    cwd=infra
    Run Process    vagrant halt --force   shell=True    cwd=infra

Test Setup
    Open Connection    ${IP_VM}
    Login    vagrant     vagrant
    Clean Ganeti
    Create Ganeti Cluster

Test Teardown
    Clean Ganeti
    Close All Connections

Create Ganeti Cluster
    ${stdout}    ${stderr}    ${rc}=    Execute Command    sudo gnt-cluster init --master-netdev=br_gnt --enabled-hypervisors=fake --enabled-disk-templates=file cluster-test    return_stdout=True    return_stderr=True    return_rc=True
    Log    ${stdout}
    Should Be Equal as Integers   0    ${rc}    msg=Cannot create ClusterVM\n${stderr}

Clean Ganeti
    Execute Command    sudo gnt-instance stop --timeout\=0 --all
    #Execute Command    sudo gnt-cluster destroy --yes-do-it
    Execute Command    sudo rm -rf /var/lib/ganeti/*
    Execute Command    /etc/init.d/ganeti restart

Create inventory
    Create File    ${INVENTORY_ABSOLUE_PATH}    [all]\ntest ansible_host=${IP_VM} ansible_user=vagrant ansible_ssh_pass=vagrant
    ${file}=    OperatingSystem.Get File    ${INVENTORY_ABSOLUE_PATH}
    Log    ${file}

Remove inventory
    Remove File    ${INVENTORY_ABSOLUE_PATH}

Run Vagrant And Get VM IP
    [Arguments]    ${debian_version}=stretch64
    #${result}=    Run Process    vagrant plugin install vagrant-libvirt    shell=True    cwd=infra
    #Log    ${result.stdout}
    #Should Be Equal as Integers   0    ${result.rc}    msg=Impossible to install libvirt provider\n${result.stderr}
    ${result}=    Run Process    vagrant up --provider\=libvirt --no-provision ${debian_version}    shell=True    cwd=infra
    Log    ${result.stdout}
    Should Be Equal as Integers   0    ${result.rc}    msg=Cannot create VM\n${result.stderr}
    ${result}=    Run Process    vagrant ssh --command "hostname -i" ${debian_version}    shell=True    cwd=infra
    Log    ${result.stdout}
    Should Be Equal as Integers   0    ${result.rc}    msg=Cannot get VM IP\n${result.stderr}
    ${IP_VM}=    Strip String    ${result.stdout}
    Log    "${IP_VM}"
    Should Not Be Empty    ${IP_VM}    msg=Cannot get VM IP\n${result.stderr}
    Set Suite Variable    ${IP_VM}

Run Ansible Playbook
    [Arguments]    ${playbook}    ${inventory}=${INVENTORY}
    ${result}=    Run Process    python3 \$(which ansible-playbook) -vvv -i ${inventory} ${playbook}    shell=True    cwd=ac_tests
    Log    ${result.stdout}
    Log    ${result.stderr}
    Should Be Equal As Integers    0    ${result.rc}    msg=Ansible Playbook have error\n${result.stderr}
