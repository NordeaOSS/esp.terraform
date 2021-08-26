#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Krzysztof Lewandowski <krzysztof.lewandowski@nordea.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: tfe_workspace_var
short_description: Create, update, and delete workspace variables
description:
- Creates, updates or deletes workspace variables.
- A variable may be referred either by its ID or by its name (key).
author:
  - Krzysztof Lewandowski (@klewan)
version_added: 0.1.0
options:
  url:
    description:
    - Terraform Enterprise URL.
    type: str
    required: false
  token:
    description:
    - All requests to Terraform Enterprise must be authenticated with a bearer token.
    - There are three kinds of token available, i.e. user tokens, team tokens and organization tokens.
    - See L(Authentication,https://www.terraform.io/docs/cloud/api/index.html#authentication).
    type: str
    required: true
  organization:
    description:
    - Organization name.
    type: str
    required: true
  workspace:
    description:
    - The workspace name or ID to manage variables for.
    type: str
    required: true        
  variable:
    description:
    - Variable to edit or remove.
    - The variable may be referred either by its id or its name (key).
    type: str
    required: false    
  attributes:
    description:
    - Definition of the attributes for the variable.
    - Required when C(state=present).       
    type: dict
    required: false      
    suboptions:
      key:
        description:
        - Name of the variable.
        type: str
        required: true    
      value:
        description:
        - The value of the variable.
        type: str
        required: false  
      description:
        description:
        - The description of the variable.
        type: str
        required: true                                             
      category:
        description:
        - Whether this is a Terraform or environment variable. 
        - Valid values are C(terraform) or C(env).
        type: str
        required: true   
      hcl:
        description:
        - Whether to evaluate the value of the variable as a string of HCL code. Has no effect for environment variables.
        type: bool
        required: false
      sensitive:
        description:
        - Whether the value is sensitive. If C(true) then the variable is written once and not visible thereafter.
        type: bool
        required: false                       
  state:
    description:
    - Whether the variable should exist or not.
    type: str
    default: present
    choices: [ absent, present ]
    required: true
  validate_certs:
    description:
      - If C(no), SSL certificates will not be validated.
      - This should only set to C(no) used on personally controlled sites using self-signed certificates.
    type: bool
    default: yes
  use_proxy:
    description:
      - If C(no), it will not use a proxy, even if one is defined in an environment variable on the target hosts.
    type: bool
    default: yes 
  sleep:
    description:
      - Number of seconds to sleep between API retries.
    type: int
    default: 5
  retries:
    description:
      - Number of retries to call Terraform API URL before failure.
    type: int
    default: 3
notes:
- Authentication must be done with U(token).
- Supports C(check_mode).
'''

EXAMPLES = r'''
- name: Create a Variable
  esp.terraform.tfe_workspace_var:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    workspace: bar
    attributes:
      "key": some_key
      "value": some_value
      "description": some description
      "category": terraform
      "hcl": false
      "sensitive": false
    state: present
    validate_certs: no

- name: Edit a Variable
  esp.terraform.tfe_workspace_var:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    workspace: bar
    variable: var-sCmHmHGSTYCp38sY
    attributes:      
      "value": new_some_value
      "description": updated variable
      "sensitive": true
    state: present
    validate_certs: no

- name: Remove a Variable
  esp.terraform.tfe_workspace_var:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    workspace: bar
    variable: AWS_SECRET_ACCESS_KEY
    state: absent
    validate_certs: no
'''

RETURN = r'''
json:
    description: Details on the variable.
    returned: success
    type: dict
    contains:
        data:
            description: Details on the variable.
            returned: success
            type: dict                  
            sample:
                attributes:
                    category: terraform
                    created-at: 2021-05-17T14:19:46.941Z
                    description: some description
                    hcl: false
                    key: some_key
                    sensitive: false
                    value: some_value
                id: var-PLmSNFWk1y5X7NqR
                links:
                    self: /api/v2/workspaces/ws-NX8cHwQMGHQohG79/vars/var-PLmSNFWk1y5X7NqR
                relationships:
                    configurable:
                        data:
                            id: ws-NX8cHwQMGHQohG79
                            type: workspaces
                        links:
                            related: /api/v2/organizations/foo/workspaces/bar
                type: vars           
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_bytes, to_native, to_text

from ansible_collections.esp.terraform.plugins.module_utils.tfe_helper import TFEHelper


def main():
    argument_spec = TFEHelper.tfe_argument_spec()
    argument_spec.update(
        organization=dict(type='str', required=True, no_log=False),
        workspace=dict(type='str', required=True, no_log=False),     
        variable=dict(type='str', required=False, no_log=False),
        state=dict(type='str', choices=['present', 'absent'], default='present'),
        attributes=dict(
            type='dict', 
            required=False, no_log=False,
        )
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,  
        required_if=[('state', 'absent', ('variable',), True), ('state', 'present', ('attributes',), True)],        
    )

    tfe = TFEHelper(module)

    organization = tfe.get_org_name_when_exists(organization=module.params['organization'])
    workspace = module.params['workspace']
    variable = module.params['variable']
    state = module.params['state']
    attributes = module.params['attributes']

    # Seed the result dict in the object
    result = dict(
        changed=False,
        state=state,
        organization=organization,
        workspace=workspace,
        json={},
    )
    if variable is not None:
        result['variable'] = variable
    if attributes is not None:
        result['attributes'] = attributes.copy()
        # Do not expose 'value' when it's marked as sensitive
        if attributes.get('sensitive', False):
            result['attributes'].pop('value', None)

    # Set organization
    try:        
        tfe.call_endpoint(tfe.api.set_org, org_name=organization)
    except Exception as e:
        module.fail_json(msg='Unable to set "%s" organization to use for org specific endpoints: %s' % (organization, to_native(e)))

    # Get the list of all workspaces without additional details
    try:        
        all_workspaces = tfe.call_endpoint(tfe.api.workspaces.list_all, include=None)
    except Exception as e:
        module.fail_json(msg='Unable to list workspaces in "%s" organization. Error: %s.' % (organization, to_native(e)) )

    # Get existing workspace ID. 
    workspace_id = None
    # Refer to a workspace by its name
    if any(w['attributes']['name'] == workspace for w in all_workspaces['data']):
        workspace_id = [w for w in all_workspaces['data'] if w['attributes']['name'] == workspace][0]['id']
    # Refer to a workspace by its ID
    elif any(w['id'] == workspace for w in all_workspaces['data']):
        workspace_id = workspace
    else:
        module.fail_json(msg='The supplied "%s" workspace does not exist in "%s" organization.' % (workspace, organization) )

    # Get the list of all variables for the supplied namespace
    try:   
        all_variables = tfe.call_endpoint(tfe.api.workspace_vars.list, workspace_id=workspace_id)
    except Exception as e:
        module.fail_json(msg='Unable to list variables in "%s" workspace. Error: %s.' % (workspace, to_native(e)) )

    # Get existing variable ID. 
    variable_id = None
    if variable is not None:
        # Refer to a variable by its name/key
        if any(v['attributes']['key'] == variable for v in all_variables['data']):
            variable_id = [v for v in all_variables['data'] if v['attributes']['key'] == variable][0]['id']
        # Refer to a variable by its ID
        elif any(v['id'] == variable for v in all_variables['data']):
            variable_id = variable
        else:
            if state == 'present':
                module.fail_json(msg='The supplied "%s" variable does not exist in "%s" workspace.' % (variable, workspace) )
    else:
        if 'key' not in attributes:
            module.fail_json(msg='`key` is required when creating a new variable.')
        # Find variable_id when 'New' variable already exists
        if any(v['attributes']['key'] == attributes['key'] for v in all_variables['data']):
            variable_id = [v for v in all_variables['data'] if v['attributes']['key'] == attributes['key']][0]['id']

    # Delete the variable if it exists and state == 'absent'
    if (state == 'absent') and (variable_id is not None):

        if not module.check_mode:
            try:        
                result['json'] = tfe.call_endpoint(tfe.api.workspace_vars.destroy, workspace_id=workspace_id, variable_id=variable_id)
            except Exception as e:
                module.fail_json(msg='Unable to delete "%s" variable from "%s" workspace. Error: %s.' % (variable, workspace, to_native(e)) )          

        result['changed'] = True
 
    # Update the variable if it exists and state == 'present'
    if (state == 'present') and (variable_id is not None):

        if attributes is not None:
            v_payload = {
              "data": {
                "id": variable_id,
                "attributes": attributes,
                "type": "vars"
              }
            }

            # Check if 'attributes' is a subset of current attributes, i.e. if there is any change
            current_attributes = [v for v in all_variables['data'] if v['id'] == variable_id][0]['attributes']         
            if not tfe.is_subset(subset=attributes, superset=current_attributes):

                if not module.check_mode:
                    try:        
                        result['json'] = tfe.call_endpoint(tfe.api.workspace_vars.update, workspace_id=workspace_id, variable_id=variable_id, payload=v_payload)
                    except Exception as e:
                        module.fail_json(msg='Unable to update "%s" variable in "%s" workspace. Error: %s.' % (variable, workspace, to_native(e)) )    

                result['changed'] = True

    # Create the variable if it does not exist and state == 'present'
    if (state == 'present') and (variable_id is None):

        if 'key' not in attributes:
            module.fail_json(msg='`key` is required when creating a new variable')

        v_payload = {
          "data": {
            "attributes": attributes,
            "type": "vars"
          }
        }

        if not module.check_mode:
            try:        
                result['json'] = tfe.call_endpoint(tfe.api.workspace_vars.create, workspace_id=workspace_id, payload=v_payload)
            except Exception as e:
                module.fail_json(msg='Unable to create "%s" variable in "%s" workspace. Error: %s.' % (variable, workspace, to_native(e)) )    
               
        result['changed'] = True

    module.exit_json(**result)


if __name__ == '__main__':
    main()