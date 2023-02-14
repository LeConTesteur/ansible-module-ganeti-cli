from typing import Dict, List, Tuple
import unittest

from ansible_collections.ganeti.cli.plugins.module_utils.builder_command_options.builders import BuilderCommandOptionsSpecAbstract
from ansible_collections.ganeti.cli.plugins.module_utils.builder_command_options import builders

# To args spec

class MockBuilderToArgsSpec:
  def __init__(self, name, value) -> None:
    self.name = name
    self.value = value

  def to_args_spec(self):
    return {'value':self.value}

class BuilderToArgsSpec(unittest.TestCase):

  def _test_to_args_spec(self, data_set:List[Tuple[BuilderCommandOptionsSpecAbstract, dict]]):
    for index, data_line in enumerate(data_set):
      builder: BuilderCommandOptionsSpecAbstract = data_line[0]
      expected:dict = data_line[1]
      self.assertEqual(builder.to_args_spec(), expected, msg='Error in line {} of data_set'.format(index+1))

  def test_BuilderCommandOptionsSpec(self):
    self._test_to_args_spec(
      [
        (builders.BuilderCommandOptionsSpec(name='root'), {}),
        (builders.BuilderCommandOptionsSpec(MockBuilderToArgsSpec('test', 'foo'), name='root'), {'test':{'value':'foo'}}),
        (builders.BuilderCommandOptionsSpec(
          MockBuilderToArgsSpec('test1', 'foo'),
          MockBuilderToArgsSpec('test2', 'bar'),
          name='root'), 
          {'test1':{'value':'foo'}, 'test2':{'value':'bar'}}
        ),
        (builders.BuilderCommandOptionsSpec(
          MockBuilderToArgsSpec('test1', 'foo'),
          MockBuilderToArgsSpec('test2', 'bar'),
          MockBuilderToArgsSpec('test3', '5'),
          MockBuilderToArgsSpec('test4', '10'),
          name='root'), 
          {'test1':{'value':'foo'}, 'test2':{'value':'bar'}, 'test3':{'value':'5'}, 'test4':{'value':'10'}}
        ),
      ]
    )
    
  def test_BuilderCommandOptionsRootSpec(self):
    self._test_to_args_spec(
      [
        (builders.BuilderCommandOptionsRootSpec(), {}),
        (builders.BuilderCommandOptionsRootSpec(MockBuilderToArgsSpec('test', 'foo')), {'test':{'value':'foo'}}),
        (builders.BuilderCommandOptionsRootSpec(
            MockBuilderToArgsSpec('test1', 'foo'),
            MockBuilderToArgsSpec('test2', 'bar'),
          ), 
          {'test1':{'value':'foo'}, 'test2':{'value':'bar'}}
        ),
        (builders.BuilderCommandOptionsRootSpec(
            MockBuilderToArgsSpec('test1', 'foo'),
            MockBuilderToArgsSpec('test2', 'bar'),
            MockBuilderToArgsSpec('test3', '5'),
            MockBuilderToArgsSpec('test4', '10'),
          ), 
          {'test1':{'value':'foo'}, 'test2':{'value':'bar'}, 'test3':{'value':'5'}, 'test4':{'value':'10'}}
        ),
      ]
    )

  def test_BuilderCommandOptionsSpecDict(self):
    self._test_to_args_spec(
      [
        (builders.BuilderCommandOptionsSpecDict(name='root'), {'type': 'dict', 'required':False, 'options':{}}),
        (builders.BuilderCommandOptionsSpecDict(
            MockBuilderToArgsSpec('test', 'foo'),
            name='root'
          ), 
         {'type': 'dict', 'required':False, 'options':{'test':{'value':'foo'}}}
        ),
        (builders.BuilderCommandOptionsSpecDict(
            MockBuilderToArgsSpec('test1', 'foo'),
            MockBuilderToArgsSpec('test2', 'bar'),
            name='root'
          ), 
          {'type': 'dict', 'required':False, 'options':{'test1':{'value':'foo'}, 'test2':{'value':'bar'}}}
        ),
        (builders.BuilderCommandOptionsSpecDict(
            MockBuilderToArgsSpec('test1', 'foo'),
            MockBuilderToArgsSpec('test2', 'bar'),
            MockBuilderToArgsSpec('test3', '5'),
            MockBuilderToArgsSpec('test4', '10'),
            name='root'
          ), 
          {'type': 'dict', 'required':False, 'options':{'test1':{'value':'foo'}, 'test2':{'value':'bar'}, 'test3':{'value':'5'}, 'test4':{'value':'10'}}}
        ),
      ]
    )

  def test_BuilderCommandOptionsSpecList(self):
    self._test_to_args_spec(
      [
        (builders.BuilderCommandOptionsSpecList(name='root'), {'type': 'list', 'required':False, 'options':{}}),
        (builders.BuilderCommandOptionsSpecList(
            MockBuilderToArgsSpec('test', 'foo'),
            name='root'
          ), 
         {'type': 'list', 'required':False, 'options':{'test':{'value':'foo'}}}
        ),
        (builders.BuilderCommandOptionsSpecList(
            MockBuilderToArgsSpec('test1', 'foo'),
            MockBuilderToArgsSpec('test2', 'bar'),
            name='root'
          ), 
          {'type': 'list', 'required':False, 'options':{'test1':{'value':'foo'}, 'test2':{'value':'bar'}}}
        ),
        (builders.BuilderCommandOptionsSpecList(
            MockBuilderToArgsSpec('test1', 'foo'),
            MockBuilderToArgsSpec('test2', 'bar'),
            MockBuilderToArgsSpec('test3', '5'),
            MockBuilderToArgsSpec('test4', '10'),
            name='root'
          ), 
          {'type': 'list', 'required':False, 'options':{'test1':{'value':'foo'}, 'test2':{'value':'bar'}, 'test3':{'value':'5'}, 'test4':{'value':'10'}}}
        ),
      ]
    )

  def test_BuilderCommandOptionsSpecElement(self):
    self._test_to_args_spec(
      [
        (builders.BuilderCommandOptionsSpecElement(name='root', type='test'), {'type': 'test', 'required':False, 'default':None}),
        (builders.BuilderCommandOptionsSpecElement(
            type='int',
            name='root',
            required=True
          ), 
         {'type': 'int', 'required':True, 'default':None}
        ),
        (builders.BuilderCommandOptionsSpecElement(
            type='bool',
            name='root',
            required=False,
            default='foo'          ), 
          {'type': 'bool', 'required':False, 'default':'foo'}
        ),
      ]
    )
    
  def test_args_spec_generation(self):
    spec = builders.BuilderCommandOptionsRootSpec(
            builders.BuilderCommandOptionsSpecElement(name='disk_template', type='str'),
            builders.BuilderCommandOptionsSpecList(
              builders.BuilderCommandOptionsSpecListSubElement(name='name', type='str'),
              builders.BuilderCommandOptionsSpecListSubElement(name='size', type='str', info_key='disk/{}', required=True),
              name="disks",
              info_key = 'Disks'
             ),
            builders.BuilderCommandOptionsSpecDict(
              builders.BuilderCommandOptionsSpecSubElement(name='memory', type='int'),
              builders.BuilderCommandOptionsSpecSubElement(name='vcpus', type='int'),
              name='backend_param',
              info_key = 'Back-end parameters',
            )
          )
    builder = builders.BuilderCommand(binary='', spec=spec)
    self.assertEqual(builder.generate_args_spec(), {
      'disk_template': {'type':'str', 'required':False, 'default':None},
      'disks': {'type':'list', 'required':False, 'options': {
        'name':{'type':'str', 'required':False, 'default':None},
        'size':{'type':'str', 'required':True, 'default':None},
      }},
      'backend_param': {'type':'dict', 'required':False, 'options': {
        'memory':{'type':'int', 'required':False, 'default':None},
        'vcpus':{'type':'int', 'required':False, 'default':None},
      }}
    })

# To options
class MockBuilderToOptions:
  def __init__(self, value) -> None:
    self.value = value
    
  def set_index(self, index):
    if index is not None:
      self.index = index

  def to_options(self, param, info): # pylance: disable=
    return ['value={},index={}'.format(self.value,self.index)]
  

class BuilderToOptions(unittest.TestCase):

  def _test_to_options(self, data_set:List[Tuple[BuilderCommandOptionsSpecAbstract, dict]]):
    for index, data_line in enumerate(data_set):
      builder: BuilderCommandOptionsSpecAbstract = data_line[0]
      param:Dict = data_line[1]
      info:Dict = data_line[2]
      expected:dict = data_line[3]
      self.assertEqual(builder.to_options(param, info), expected, msg='Error in line {} of data_set'.format(index+1))

  def test_BuilderCommandOptionsSpecSubElement(self):
    self._test_to_options([
      (builders.BuilderCommandOptionsSpecSubElement(type='', index=0,name='test',info_key='Test'), {}, {}, []),
      (builders.BuilderCommandOptionsSpecSubElement(type='', index=0,name='test',info_key='Test'), {'test':1}, {}, ['test=1']),
      (builders.BuilderCommandOptionsSpecSubElement(type='', index=0,name='test',info_key='Test'), {}, {'Test':1}, ['test=default']),
      (builders.BuilderCommandOptionsSpecSubElement(type='', index=0,name='test',info_key='Test', default_ganeti=builders.NONE_VALUE), {}, {'Test':1}, ['test=None']),
      (builders.BuilderCommandOptionsSpecSubElement(type='', index=0,name='test',info_key='Test'), {'test':1}, {'Test':1}, []),
      (builders.BuilderCommandOptionsSpecSubElement(type='', index=0,name='test',info_key='Test'), {'test':1}, {'Test':2}, ['test=1']),
      (builders.BuilderCommandOptionsSpecSubElement(type='', index=0,name='test',info_key='Test/{}'), {'test':1}, {'Test':1}, ['test=1']),
      (builders.BuilderCommandOptionsSpecSubElement(type='', index=0,name='test',info_key='Test/{}'), {'test':1}, {'Test/0':1}, []),
      (builders.BuilderCommandOptionsSpecSubElement(type='', index=0,name='test',info_key='Test/{}'), {'test':1}, {'Test/1':1}, ['test=1']),
      (builders.BuilderCommandOptionsSpecSubElement(type='', index=0,name='test',info_key='Test/{}'), {}, {'Test/0':1}, ['test=default']),
    ])
    
  def test_BuilderCommandOptionsSpecElement(self):
    self._test_to_options([
      (builders.BuilderCommandOptionsSpecElement(type='', name='test',info_key='Test'), {}, {}, []),
      (builders.BuilderCommandOptionsSpecElement(type='', name='test',info_key='Test'), {'test':1}, {}, ['--test=1']),
      (builders.BuilderCommandOptionsSpecElement(type='', name='test',info_key='Test'), {}, {'Test':1}, ['--test=default']),
      (builders.BuilderCommandOptionsSpecElement(type='', name='test',info_key='Test', default_ganeti=builders.NONE_VALUE), {}, {'Test':1}, ['--test=None']),
      (builders.BuilderCommandOptionsSpecElement(type='', name='test',info_key='Test'), {'test':1}, {'Test':1}, []),
      (builders.BuilderCommandOptionsSpecElement(type='', name='test',info_key='Test'), {'test':1}, {'Test':2}, ['--test=1']),
      (builders.BuilderCommandOptionsSpecElement(type='', name='test',info_key='Test/{}'), {'test':1}, {'Test':1}, ['--test=1']),
    ])
    
  def test__BuilderCommandOptionsSpecListElement(self):
    self._test_to_options([
      (builders._BuilderCommandOptionsSpecListElement(index=0), {}, {}, ['']),
      (builders._BuilderCommandOptionsSpecListElement(MockBuilderToOptions(value=0), index=0), {}, {}, ['value=0,index=0']),
      (builders._BuilderCommandOptionsSpecListElement(MockBuilderToOptions(value=0),MockBuilderToOptions(value=2), index=3), {}, {}, ['value=0,index=3,value=2,index=3']),
    ])
    
  def test_BuilderCommandOptionsSpecList(self):
        self._test_to_options([
      (builders.BuilderCommandOptionsSpecList(name='test', info_key='Tests'), {}, {}, ['']),
      (
        builders.BuilderCommandOptionsSpecList(
          builders.BuilderCommandOptionsSpecSubElement(type='', name='name',info_key='name'),
          name='test', info_key='Tests', no_option='--no-options'
        ), 
        {}, 
        {}, 
        ['--no-options']
      ),
      (
        builders.BuilderCommandOptionsSpecList(
          builders.BuilderCommandOptionsSpecSubElement(type='', name='name',info_key='name'),
          name='test', info_key='Tests', no_option='--no-options'
        ), 
        {'test':[]}, 
        {}, 
        ['--no-options']
      ),
      (
        builders.BuilderCommandOptionsSpecList(
          builders.BuilderCommandOptionsSpecSubElement(type='', name='name',info_key='name'),
          name='test', info_key='Tests', no_option='--no-options'
        ), 
        {'test':[{'name':'foo'}]}, 
        {}, 
        ['--test', '0:add:name=foo']
      ),
    ])
if __name__ == '__main__':
    unittest.main()