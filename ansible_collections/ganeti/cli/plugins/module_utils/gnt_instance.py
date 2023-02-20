"""
Class GntInstance
"""
from typing import Callable, Dict, List, Tuple
import re


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

def parse_state(state:str) -> Tuple[bool, bool]:
    """Parse the string for extract state and admin_state

    Args:
        state (str): The string return by ganeti

    Returns:
        Tuple[bool, bool]: state and admin_state
    """
    match = re.match(
        r'configured to be (?P<admin_state>\w+), actual state is (?P<state>\w+)',
        state
    )
    return match.group('admin_state'),  match.group('state')

def parse_info_instances(*_, stdout: str, **__) -> List[Dict]:
    """Parse info return of ganeti commands

    Args:
        stdout (str): the information

    Returns:
        List[Dict]: Lsit of information parsed
    """
    info_instances = parse_from_stdout(stdout=stdout)
    l_info = []
    for info_instance in info_instances:
        admin_state, state = parse_state(info_instance['State'])
        info_instance['name'] = info_instance['Instance name'].strip()
        info_instance['state'] = state
        info_instance['admin_state'] = admin_state
        l_info.append(info_instance)
    return l_info

disk_templates = ['sharedfile', 'diskless', 'plain', 'gluster', 'blockdev',
                  'drbd', 'ext', 'file', 'rbd']
hypervisor_choices = ['chroot', 'xen-pvm', 'kvm', 'xen-hvm', 'lxc', 'fake']
nic_types_choices = ['bridged', 'openvswitch']

disks_options = [
    BuilderCommandOptionsSpecListSubElement(name='name', type="str", require=True),
    BuilderCommandOptionsSpecListSubElement(
        name='size', type="int", require=True, create_only=True),
    BuilderCommandOptionsSpecListSubElement(name='spindles', type="str", require=True),
    BuilderCommandOptionsSpecListSubElement(name='metavg', type="str", require=True),
    BuilderCommandOptionsSpecListSubElement(name='access', type="str", require=True),
    BuilderCommandOptionsSpecListSubElement(name='access', type="str", require=True),
]

nics_options = [
    BuilderCommandOptionsSpecListSubElement(name='name', type="str", require=True),
    BuilderCommandOptionsSpecListSubElement(name='link', type="str", require=True),
    BuilderCommandOptionsSpecListSubElement(name='vlan', type="str", require=False),
    BuilderCommandOptionsSpecListSubElement(
        name='mode', type="str", default='bridged',require=True),
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
    BuilderCommandOptionsSpecElement(
        name='disk-template', type='str', default='plain', choices=disk_templates,
        info_key='Disk template'
    ),
    BuilderCommandOptionsSpecList(
        *disks_options,
        name='disk',
        info_key='Disks'
    ),
    BuilderCommandOptionsSpecElement(
        name='hypervisor', type='str', default='kvm', choices=hypervisor_choices,
        info_key='Hypervisor'
    ),
    BuilderCommandOptionsSpecElementOnlyCreate(name='iallocator', type='str'),
    BuilderCommandOptionsSpecList(
        *nics_options,
        name='net',
        info_key='NICs',
        no_option='--no-nics --ignore-ipolicy'
    ),
    BuilderCommandOptionsSpecElement(
        name='os-type', type='str', required=True, info_key='Operating system'),
    BuilderCommandOptionsSpecDict(
        *hypervisor_params,
        name='hypervisor-parameters',
        info_key='Hypervisor parameters'
    ),
    BuilderCommandOptionsSpecDict(
        *backend_param,
        name='backend-parameters',
        info_key='Back-end parameters'
    ),
    BuilderCommandOptionsSpecStateElement(name='name-check', create_only=True),
    BuilderCommandOptionsSpecStateElement(name='ip-check', create_only=True),
    BuilderCommandOptionsSpecStateElement(name='conflicts-check', create_only=True),
    BuilderCommandOptionsSpecStateElement(name='install', create_only=True),
    BuilderCommandOptionsSpecStateElement(name='start', default=False, create_only=True),
    BuilderCommandOptionsSpecStateElement(name='wait-for-sync'),
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
            BuilderCommand(builder_gnt_instance_spec).generate(
                module_params=params, info_data={}, create=True
            ),
            name,
            command='add'
        )

    def modify(self, name:str, params: dict, vm_info: dict):
        """
        Run command: gnt-instance modify
        """
        return self._run_command(
            BuilderCommand(builder_gnt_instance_spec).generate(
                module_params=params, info_data=vm_info
            ),
            name,
            command='modify'
        )

    def config_and_remote_have_different(self, params: dict, vm_info) -> bool:
        """Compute different between cofig and remote information

        Args:
            params (dict): Param of ansible module
            vm_info (_type_): Remote vm information

        Returns:
            bool: Have different
        """
        options = BuilderCommand(builder_gnt_instance_spec).generate(
            module_params=params, info_data=vm_info
        )
        return bool(options.strip())


    def info(self, name:str) -> List[Dict]:
        """Return Information of instances

        Args:
            name (str): name of instance

        Returns:
            List[Dict]: Instances information
        """
        return self._run_command(
            name,
            command='info',
            parser=parse_info_instances,
            return_none_if_error=True
        )
