import unittest

from collections import OrderedDict, namedtuple

from ansible_collections.lecontesteur.ganeti_cli.plugins.module_utils.gnt_instance_list import (
  parse_ganeti_list_output_line,
  build_gnt_instance_list_arguments,
  subheaders,
  GntListOption,
  merge_alias_headers,
  field_headers
)


TestCaseData = namedtuple('TestCaseData', ['input', 'expected'])

expected_headers = ['name', 'nic_names', 'nic_modes', 'nic_vlans', 'disk_sizes', 'hvparams']
gnt_instance_list_base = ['--no-headers', "--separator='--##'", '--output']

data_tests_full_headers = [
  TestCaseData(
    "vm1--##[None, None]--##bridged,openvswitch--##[None, u'']--##5120,122880--##{'spice_password_file': u'', 'nic_type': 'e1000', 'use_localtime': False, 'root_path': u'', 'spice_use_tls': False, 'vnc_x509_path': u'', 'vnc_bind_address': '0.0.0.0', 'vnc_password_file': u'', 'cdrom2_image_path': u'', 'usb_mouse': u'', 'vhost_net': False, 'spice_streaming_video': u'', 'spice_use_vdagent': True, 'use_chroot': False, 'spice_tls_ciphers': 'HIGH:-DES:-3DES:-EXPORT:-DH', 'machine_version': u'', 'migration_downtime': 30, 'cpu_sockets': 0, 'vnc_x509_verify': False, 'soundhw': u'', 'kernel_args': 'ro', 'cdrom_image_path': u'', 'kvm_extra': u'', 'spice_ip_version': 0, 'vga': u'', 'cpu_cores': 0, 'cpu_mask': 'all', 'migration_caps': u'', 'disk_aio': 'threads', 'disk_cache': 'default', 'kvm_path': '/usr/bin/kvm', 'kernel_path': u'', 'initrd_path': u'', 'spice_jpeg_wan_compression': u'', 'vnc_tls': False, 'cdrom_disk_type': u'', 'boot_order': 'disk', 'security_domain': u'', 'serial_console': True, 'spice_bind': u'', 'spice_zlib_glz_wan_compression': u'', 'kvm_flag': u'', 'cpu_threads': 0, 'vnet_hdr': True, 'disk_type': 'ide', 'usb_devices': u'', 'spice_image_compression': u'', 'spice_playback_compression': True, 'security_model': 'none', 'user_shutdown': False, 'serial_speed': 38400, 'reboot_behavior': 'reboot', 'floppy_image_path': u'', 'acpi': True, 'keymap': u'', 'cpu_type': u'', 'virtio_net_queues': 1, 'mem_path': u''}",
    ["vm1", [None, None], ["bridged", "openvswitch"], [None, ''], ["5120","122880"], {'spice_password_file': u'', 'nic_type': 'e1000', 'use_localtime': False, 'root_path': u'', 'spice_use_tls': False, 'vnc_x509_path': u'', 'vnc_bind_address': '0.0.0.0', 'vnc_password_file': u'', 'cdrom2_image_path': u'', 'usb_mouse': u'', 'vhost_net': False, 'spice_streaming_video': u'', 'spice_use_vdagent': True, 'use_chroot': False, 'spice_tls_ciphers': 'HIGH:-DES:-3DES:-EXPORT:-DH', 'machine_version': u'', 'migration_downtime': 30, 'cpu_sockets': 0, 'vnc_x509_verify': False, 'soundhw': u'', 'kernel_args': 'ro', 'cdrom_image_path': u'', 'kvm_extra': u'', 'spice_ip_version': 0, 'vga': u'', 'cpu_cores': 0, 'cpu_mask': 'all', 'migration_caps': u'', 'disk_aio': 'threads', 'disk_cache': 'default', 'kvm_path': '/usr/bin/kvm', 'kernel_path': u'', 'initrd_path': u'', 'spice_jpeg_wan_compression': u'', 'vnc_tls': False, 'cdrom_disk_type': u'', 'boot_order': 'disk', 'security_domain': u'', 'serial_console': True, 'spice_bind': u'', 'spice_zlib_glz_wan_compression': u'', 'kvm_flag': u'', 'cpu_threads': 0, 'vnet_hdr': True, 'disk_type': 'ide', 'usb_devices': u'', 'spice_image_compression': u'', 'spice_playback_compression': True, 'security_model': 'none', 'user_shutdown': False, 'serial_speed': 38400, 'reboot_behavior': 'reboot', 'floppy_image_path': u'', 'acpi': True, 'keymap': u'', 'cpu_type': u'', 'virtio_net_queues': 1, 'mem_path': u''}]
  ),
  TestCaseData(
    "vm2--##[None, None, None, None]--##bridged,openvswitch,openvswitch,openvswitch--##[None, u'', u'', u'']--##12288--##{'spice_password_file': u'', 'nic_type': 'e1000', 'use_localtime': False, 'root_path': u'', 'spice_use_tls': False, 'vnc_x509_path': u'', 'vnc_bind_address': '0.0.0.0', 'vnc_password_file': u'', 'cdrom2_image_path': u'', 'usb_mouse': u'', 'vhost_net': False, 'spice_streaming_video': u'', 'spice_use_vdagent': True, 'use_chroot': False, 'spice_tls_ciphers': 'HIGH:-DES:-3DES:-EXPORT:-DH', 'machine_version': u'', 'migration_downtime': 30, 'cpu_sockets': 0, 'vnc_x509_verify': False, 'soundhw': u'', 'kernel_args': 'ro', 'cdrom_image_path': u'', 'kvm_extra': u'', 'spice_ip_version': 0, 'vga': u'', 'cpu_cores': 0, 'cpu_mask': 'all', 'migration_caps': u'', 'disk_aio': 'threads', 'disk_cache': 'default', 'kvm_path': '/usr/bin/kvm', 'kernel_path': u'', 'initrd_path': u'', 'spice_jpeg_wan_compression': u'', 'vnc_tls': False, 'cdrom_disk_type': u'', 'boot_order': 'disk', 'security_domain': u'', 'serial_console': True, 'spice_bind': u'', 'spice_zlib_glz_wan_compression': u'', 'kvm_flag': u'', 'cpu_threads': 0, 'vnet_hdr': True, 'disk_type': 'ide', 'usb_devices': u'', 'spice_image_compression': u'', 'spice_playback_compression': True, 'security_model': 'none', 'user_shutdown': False, 'serial_speed': 38400, 'reboot_behavior': 'reboot', 'floppy_image_path': u'', 'acpi': True, 'keymap': u'', 'cpu_type': u'', 'virtio_net_queues': 1, 'mem_path': u''}",
    ["vm2", [None, None, None, None], ["bridged","openvswitch","openvswitch","openvswitch"], [None, u'', u'', u''], ["12288"], {'spice_password_file': u'', 'nic_type': 'e1000', 'use_localtime': False, 'root_path': u'', 'spice_use_tls': False, 'vnc_x509_path': u'', 'vnc_bind_address': '0.0.0.0', 'vnc_password_file': u'', 'cdrom2_image_path': u'', 'usb_mouse': u'', 'vhost_net': False, 'spice_streaming_video': u'', 'spice_use_vdagent': True, 'use_chroot': False, 'spice_tls_ciphers': 'HIGH:-DES:-3DES:-EXPORT:-DH', 'machine_version': u'', 'migration_downtime': 30, 'cpu_sockets': 0, 'vnc_x509_verify': False, 'soundhw': u'', 'kernel_args': 'ro', 'cdrom_image_path': u'', 'kvm_extra': u'', 'spice_ip_version': 0, 'vga': u'', 'cpu_cores': 0, 'cpu_mask': 'all', 'migration_caps': u'', 'disk_aio': 'threads', 'disk_cache': 'default', 'kvm_path': '/usr/bin/kvm', 'kernel_path': u'', 'initrd_path': u'', 'spice_jpeg_wan_compression': u'', 'vnc_tls': False, 'cdrom_disk_type': u'', 'boot_order': 'disk', 'security_domain': u'', 'serial_console': True, 'spice_bind': u'', 'spice_zlib_glz_wan_compression': u'', 'kvm_flag': u'', 'cpu_threads': 0, 'vnet_hdr': True, 'disk_type': 'ide', 'usb_devices': u'', 'spice_image_compression': u'', 'spice_playback_compression': True, 'security_model': 'none', 'user_shutdown': False, 'serial_speed': 38400, 'reboot_behavior': 'reboot', 'floppy_image_path': u'', 'acpi': True, 'keymap': u'', 'cpu_type': u'', 'virtio_net_queues': 1, 'mem_path': u''}]
  ),
  TestCaseData(
    "vm3--##[None]--##bridged--##[None]--##20480--##{'spice_password_file': u'', 'nic_type': 'e1000', 'use_localtime': False, 'root_path': u'', 'spice_use_tls': False, 'vnc_x509_path': u'', 'vnc_bind_address': '0.0.0.0', 'vnc_password_file': u'', 'cdrom2_image_path': u'', 'usb_mouse': u'', 'vhost_net': False, 'spice_streaming_video': u'', 'spice_use_vdagent': True, 'use_chroot': False, 'spice_tls_ciphers': 'HIGH:-DES:-3DES:-EXPORT:-DH', 'machine_version': u'', 'migration_downtime': 30, 'cpu_sockets': 0, 'vnc_x509_verify': False, 'soundhw': u'', 'kernel_args': 'ro', 'cdrom_image_path': u'', 'kvm_extra': u'', 'spice_ip_version': 0, 'vga': u'', 'cpu_cores': 0, 'cpu_mask': 'all', 'migration_caps': u'', 'disk_aio': 'threads', 'disk_cache': 'default', 'kvm_path': '/usr/bin/kvm', 'kernel_path': u'', 'initrd_path': u'', 'spice_jpeg_wan_compression': u'', 'vnc_tls': False, 'cdrom_disk_type': u'', 'boot_order': 'disk', 'security_domain': u'', 'serial_console': True, 'spice_bind': u'', 'spice_zlib_glz_wan_compression': u'', 'kvm_flag': u'', 'cpu_threads': 0, 'vnet_hdr': True, 'disk_type': 'ide', 'usb_devices': u'', 'spice_image_compression': u'', 'spice_playback_compression': True, 'security_model': 'none', 'user_shutdown': False, 'serial_speed': 38400, 'reboot_behavior': 'reboot', 'floppy_image_path': u'', 'acpi': True, 'keymap': u'', 'cpu_type': u'', 'virtio_net_queues': 1, 'mem_path': u''}",
    ["vm3", [None], ["bridged"], [None], ["20480"], {'spice_password_file': u'', 'nic_type': 'e1000', 'use_localtime': False, 'root_path': u'', 'spice_use_tls': False, 'vnc_x509_path': u'', 'vnc_bind_address': '0.0.0.0', 'vnc_password_file': u'', 'cdrom2_image_path': u'', 'usb_mouse': u'', 'vhost_net': False, 'spice_streaming_video': u'', 'spice_use_vdagent': True, 'use_chroot': False, 'spice_tls_ciphers': 'HIGH:-DES:-3DES:-EXPORT:-DH', 'machine_version': u'', 'migration_downtime': 30, 'cpu_sockets': 0, 'vnc_x509_verify': False, 'soundhw': u'', 'kernel_args': 'ro', 'cdrom_image_path': u'', 'kvm_extra': u'', 'spice_ip_version': 0, 'vga': u'', 'cpu_cores': 0, 'cpu_mask': 'all', 'migration_caps': u'', 'disk_aio': 'threads', 'disk_cache': 'default', 'kvm_path': '/usr/bin/kvm', 'kernel_path': u'', 'initrd_path': u'', 'spice_jpeg_wan_compression': u'', 'vnc_tls': False, 'cdrom_disk_type': u'', 'boot_order': 'disk', 'security_domain': u'', 'serial_console': True, 'spice_bind': u'', 'spice_zlib_glz_wan_compression': u'', 'kvm_flag': u'', 'cpu_threads': 0, 'vnet_hdr': True, 'disk_type': 'ide', 'usb_devices': u'', 'spice_image_compression': u'', 'spice_playback_compression': True, 'security_model': 'none', 'user_shutdown': False, 'serial_speed': 38400, 'reboot_behavior': 'reboot', 'floppy_image_path': u'', 'acpi': True, 'keymap': u'', 'cpu_type': u'', 'virtio_net_queues': 1, 'mem_path': u''}]
  ),
  TestCaseData(
    "vm4--##[None, None, None, None, None]--##bridged,bridged,bridged,bridged,bridged--##[None, None, None, None, None]--##20480--##{'spice_password_file': u'', 'nic_type': 'e1000', 'use_localtime': False, 'root_path': u'', 'spice_use_tls': False, 'vnc_x509_path': u'', 'vnc_bind_address': '0.0.0.0', 'vnc_password_file': u'', 'cdrom2_image_path': u'', 'usb_mouse': u'', 'vhost_net': False, 'spice_streaming_video': u'', 'spice_use_vdagent': True, 'use_chroot': False, 'spice_tls_ciphers': 'HIGH:-DES:-3DES:-EXPORT:-DH', 'machine_version': u'', 'migration_downtime': 30, 'cpu_sockets': 0, 'vnc_x509_verify': False, 'soundhw': u'', 'kernel_args': 'ro', 'cdrom_image_path': u'', 'kvm_extra': u'', 'spice_ip_version': 0, 'vga': u'', 'cpu_cores': 0, 'cpu_mask': 'all', 'migration_caps': u'', 'disk_aio': 'threads', 'disk_cache': 'default', 'kvm_path': '/usr/bin/kvm', 'kernel_path': u'', 'initrd_path': u'', 'spice_jpeg_wan_compression': u'', 'vnc_tls': False, 'cdrom_disk_type': u'', 'boot_order': 'disk', 'security_domain': u'', 'serial_console': True, 'spice_bind': u'', 'spice_zlib_glz_wan_compression': u'', 'kvm_flag': u'', 'cpu_threads': 0, 'vnet_hdr': True, 'disk_type': 'ide', 'usb_devices': u'', 'spice_image_compression': u'', 'spice_playback_compression': True, 'security_model': 'none', 'user_shutdown': False, 'serial_speed': 38400, 'reboot_behavior': 'reboot', 'floppy_image_path': u'', 'acpi': True, 'keymap': u'', 'cpu_type': u'', 'virtio_net_queues': 1, 'mem_path': u''}",
    ["vm4", [None, None, None, None, None], ["bridged","bridged","bridged","bridged", "bridged"], [None, None, None, None, None], ["20480"], {'spice_password_file': u'', 'nic_type': 'e1000', 'use_localtime': False, 'root_path': u'', 'spice_use_tls': False, 'vnc_x509_path': u'', 'vnc_bind_address': '0.0.0.0', 'vnc_password_file': u'', 'cdrom2_image_path': u'', 'usb_mouse': u'', 'vhost_net': False, 'spice_streaming_video': u'', 'spice_use_vdagent': True, 'use_chroot': False, 'spice_tls_ciphers': 'HIGH:-DES:-3DES:-EXPORT:-DH', 'machine_version': u'', 'migration_downtime': 30, 'cpu_sockets': 0, 'vnc_x509_verify': False, 'soundhw': u'', 'kernel_args': 'ro', 'cdrom_image_path': u'', 'kvm_extra': u'', 'spice_ip_version': 0, 'vga': u'', 'cpu_cores': 0, 'cpu_mask': 'all', 'migration_caps': u'', 'disk_aio': 'threads', 'disk_cache': 'default', 'kvm_path': '/usr/bin/kvm', 'kernel_path': u'', 'initrd_path': u'', 'spice_jpeg_wan_compression': u'', 'vnc_tls': False, 'cdrom_disk_type': u'', 'boot_order': 'disk', 'security_domain': u'', 'serial_console': True, 'spice_bind': u'', 'spice_zlib_glz_wan_compression': u'', 'kvm_flag': u'', 'cpu_threads': 0, 'vnet_hdr': True, 'disk_type': 'ide', 'usb_devices': u'', 'spice_image_compression': u'', 'spice_playback_compression': True, 'security_model': 'none', 'user_shutdown': False, 'serial_speed': 38400, 'reboot_behavior': 'reboot', 'floppy_image_path': u'', 'acpi': True, 'keymap': u'', 'cpu_type': u'', 'virtio_net_queues': 1, 'mem_path': u''}]
  ),
]


class TestGanetiInstanceList(unittest.TestCase):

  def test_subheaders(self):
    self.assertEqual(len(subheaders()), 0)
    self.assertEqual(len(subheaders('name')), 1)
    self.assertEqual(len(subheaders('name', 'nic_names')), 2)
    self.assertDictEqual(
      subheaders('name', 'nic_names'),
      OrderedDict(
        name=GntListOption('name', 'str'),
        nic_names=GntListOption('nic.names', 'list'),
      )
    )

  def test_parse_with_headers(self):
    headers = subheaders(*expected_headers)
    for data in data_tests_full_headers:
      self.assertEqual(
        dict(
          zip(
            expected_headers,
            data.expected
          )
        ), 
        parse_ganeti_list_output_line(stdout=data.input, headers=headers)
      )

  def test_build_gnt_instance_list_arguments_multi_headers_and_names(self):
    self.assertEqual(
      build_gnt_instance_list_arguments('toto', 'test', header_names=['name', 'nic_names', 'nic_modes']),
      gnt_instance_list_base + ['name,nic.names,nic.modes', 'toto', "test"]
    )

  def test_build_gnt_instance_list_arguments_multi_headers_one_name(self):
    self.assertEqual(
      build_gnt_instance_list_arguments('test', header_names=['name', 'nic_names']),
      gnt_instance_list_base + ['name,nic.names', "test"]
    )

  def test_build_gnt_instance_list_arguments_one_header_and_no_name(self):
    self.assertEqual(
      build_gnt_instance_list_arguments(header_names=['name']),
      gnt_instance_list_base + ['name']
    )
  def test_build_gnt_instance_list_arguments_error_headers(self):
    self.assertEqual(
      build_gnt_instance_list_arguments('test', header_names=None),
      gnt_instance_list_base + 
      [merge_alias_headers(field_headers)] +
      ['test']
    )

if __name__ == '__main__':
    unittest.main()