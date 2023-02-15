"""
Class GntInstance
"""
from typing import Callable, List
import re
from flatdict import FlatterDict

from ansible_collections.ganeti.cli.plugins.module_utils.gnt_command import (
  GntCommand,
)
from ansible_collections.ganeti.cli.plugins.module_utils.gnt_instance_list import (
  build_gnt_instance_list_arguments,
  parse_ganeti_list_output
)

from ansible_collections.ganeti.cli.plugins.module_utils.parse_info_response import (
  parse_from_stdout
)

from ansible_collections.ganeti.cli.plugins.module_utils.builder_command_options.builders import (
    BuilderCommand,
    BuilderCommandOptionsRootSpec,
    BuilderCommandOptionsSpecDict,
    BuilderCommandOptionsSpecElement,
    BuilderCommandOptionsSpecElementOnlyCreate,
    BuilderCommandOptionsSpecList,
    BuilderCommandOptionsSpecListSubElement,
    BuilderCommandOptionsSpecStateElement,
    BuilderCommandOptionsSpecSubElement
)


GNT_INSTALL_CMD_DEFAULT = 'gnt-instance'

def parse_state(state:str):
    match = re.match(r'configured to be (?P<admin_state>\w+), actual state is (?P<state>\w+)', state)
    return match.group('admin_state'),  match.group('state')

def parse_info_instances(*_, stdout: str, **__) -> List[FlatterDict]:
    d_info = parse_from_stdout(stdout=stdout)
    l_info = []
    for k, value in d_info.as_dict().items():
        admin_state, state = parse_state(value['state'])
        d_info[k]['state'] = state
        d_info[k]['admin_state'] = admin_state
        l_info.append(d_info[k])
    print(l_info)
    return l_info

disk_templates = ['sharedfile', 'diskless', 'plain', 'gluster', 'blockdev',
                  'drbd', 'ext', 'file', 'rbd']
hypervisor_choices = ['chroot', 'xen-pvm', 'kvm', 'xen-hvm', 'lxc', 'fake']
nic_types_choices = ['bridged', 'openvswitch']

disks_options = [
    BuilderCommandOptionsSpecListSubElement(name='name', type="str", require=True),
    BuilderCommandOptionsSpecListSubElement(name='size', type="int", require=True),
    BuilderCommandOptionsSpecListSubElement(name='spindles', type="str", require=True),
    BuilderCommandOptionsSpecListSubElement(name='metavg', type="str", require=True),
    BuilderCommandOptionsSpecListSubElement(name='access', type="str", require=True),
    BuilderCommandOptionsSpecListSubElement(name='access', type="str", require=True),
]

hypervisor_params = [
    BuilderCommandOptionsSpecSubElement(name='kernel_args', type='str'),
    BuilderCommandOptionsSpecSubElement(name='kernel_path', type='str'),
]

backend_param = [
    BuilderCommandOptionsSpecSubElement(name='memory', type='int'),
    BuilderCommandOptionsSpecSubElement(name='vcpus', type='int'),
]

builder_gnt_instance_spec = BuilderCommandOptionsRootSpec(
    BuilderCommandOptionsSpecElement(name='disk_template', type='str', default='plain', choices=disk_templates),
    BuilderCommandOptionsSpecList(
        *disks_options,
        name='disk'
    ),
    BuilderCommandOptionsSpecElement(name='hypervisor', type='str', default='kvm', choices=hypervisor_choices),
    BuilderCommandOptionsSpecElementOnlyCreate(name='iallocator', type='str'),
    BuilderCommandOptionsSpecList(
        *disks_options,
        name='net'
    ),
    BuilderCommandOptionsSpecElement(name='os-type', type='str', required=True),
    BuilderCommandOptionsSpecDict(
        *hypervisor_params,
        name='hypervisor-params'
    ),
    BuilderCommandOptionsSpecDict(
        *backend_param,
        name='backend-params'
    ),
    BuilderCommandOptionsSpecStateElement(name='name-check', type=bool),
    BuilderCommandOptionsSpecStateElement(name='ip-check', type=bool)
)

class GntInstance(GntCommand):
    """
    Class GntInstance
    """
    def __init__(self, run_function: Callable, error_function: Callable, binary: str=None) -> None:
        super().__init__(run_function, error_function, binary or GNT_INSTALL_CMD_DEFAULT)


    def reboot(self, name:str, timeout:bool=0):
        """
        Builder of options of reboot
        """
        return self._run_command(
            "--shutdown-timeout={}".format(timeout),
            name,
            command='reboot',

        )

    def stop(self, name:str, timeout:int=0, force:bool=False):
        """
        Builder of options of stop
        """
        return self._run_command(
            "--timeout={}".format(timeout),
            "--force" if force else "",
            name,
            command='stop'
        )

    def start(self, name:str, start:bool=False):
        """
        Builder of options of start
        """
        return self._run_command(
            "--no-start" if not start else "",
            name,
            command='start'
        )

    def remove(self, name:str):
        """
        Builder of options of remove
        """
        return self._run_command(
            "--dry-run",
            "--force",
            name,
            command='remove'
        )

    def list(self, *names:List[str], header_names: List[str] = None) -> List:
        """Run gnt-instance list. Get all information on instances.

        Args:
            names (list[str]): name of instances to view
            headers (List[str]): Column to view for instances.
                Defaults to None.

        Returns:
            str: The return of command
        """
        return self._run_command(
            *build_gnt_instance_list_arguments(*names, header_names=header_names),
            command='list',
            parser=parse_ganeti_list_output,
            return_none_if_error=True
        )

    def add(self, name:str, params: dict):
        """
        Run command: gnt-instance add
        """
        return self._run_command(
            BuilderCommand(builder_gnt_instance_spec).generate(params, {}),
            name,
            command='add'
        )

    def modify(self, name:str, params: dict, vm_info: dict):
        """
        Run command: gnt-instance modify
        """
        return self.run_function(
            BuilderCommand(builder_gnt_instance_spec).generate(params, vm_info),
            name,
            command='modify'
        )

    def config_and_remote_have_different(self, params: dict, vm_info) -> bool:
        options = BuilderCommand(builder_gnt_instance_spec).generate(params, vm_info)
        return bool(options.strip())


    def info(self, name:str) -> List[FlatterDict]:
        self._run_command(
            name,
            command='info',
            parser=parse_info_instances,
            return_none_if_error=True
        )