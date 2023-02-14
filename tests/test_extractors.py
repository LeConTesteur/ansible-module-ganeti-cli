import datetime
import unittest

from ansible_collections.ganeti.cli.plugins.module_utils.builder_command_options import extractors

class TestBuildCmmandOptionsExtractors(unittest.TestCase):
  def _test_extractor(self, extractor, data_set):
    for index, data_line in enumerate(data_set):
      data, keys, expected = data_line
      self.assertEqual(extractor(data, keys), expected, msg='Error in line {} of data_set'.format(index+1))
  
    def test_recursive_get(self):
      self._test_extractor(
        extractor=extractors.recursive_get,
        data_set=[
          ({}, ['test'], None),
          ({'test': 'foo'}, [], None),
          ({'test': {'foo':'bar'}}, ['test', 'foo'], 'bar'),
          ({'test': {'foo':5}}, ['test', 'foo'], 5),
          ({'test': {'foo':{'bar':'5'}}}, ['test', 'foo'], {'bar':'5'}),
        ]
      )
  
  def test_value_info_extractor(self):
    self._test_extractor(
      extractor=extractors.value_info_extractor,
      data_set=[
        ({}, ['test'], None),
        ({'test': 'foo'}, [], None),
        ({'test': {'foo':'bar'}}, ['test', 'foo'], 'bar'),
        ({'test': {'foo':5}}, ['test', 'foo'], 5),
        ({'test': {'foo':'10'}}, ['test', 'foo'], 10),
        ({'test': {'foo':{'bar':'2023-02-01'}}}, ['test', 'foo', 'bar'], datetime.date(2023, 2, 1)),
      ]
    )
    
  def test_size_param_info_extractor(self):
    self._test_extractor(
      extractor=extractors.size_param_info_extractor,
      data_set=[
        ({}, ['test'], None),
        ({'test': 'foo'}, [], None),
        ({'test': {'foo':'bar'}}, ['test', 'foo'], None),
        ({'test': {'foo':5}}, ['test', 'foo'], None),
        ({'test': {'foo':'10'}}, ['test', 'foo'], None),
        ({'test': {'foo':'4G'}}, ['test', 'foo'], '4.0G'),
        ({'test': {'foo':'10G'}}, ['test', 'foo'], '10.0G'),
        ({'test': {'foo':'12.0G'}}, ['test', 'foo'], '12.0G'),
        ({'test': {'foo':'1234.15G'}}, ['test', 'foo'], '1234.15G'),
        ({'test': {'foo':'file, size 15.4G'}}, ['test', 'foo'], '15.4G'),
        ({'test': {'foo':'file, size  1.4G'}}, ['test', 'foo'], '1.4G'),
        ({'test': {'foo':'file,   size   1234.4G'}}, ['test', 'foo'], '1234.4G'),
      ]
    )

if __name__ == '__main__':
    unittest.main()