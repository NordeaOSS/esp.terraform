#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Krzysztof Lewandowski <krzysztof.lewandowski@nordea.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: tfe_workspace_var_info
short_description: List workspace variables
description:
- Lists workspace variables.
- Details on a variable can be retrieved either by its ID or by its name (key).
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
    - The Workspace name or ID to list variables for.
    type: str
    required: true    
  variable:
    description:
    - List of variables to retrieve details for.
    - This can be '*' which means all variables.
    - One may refer to a variable either by its ID or its name (key).
    type: list
    required: false
    default: [ '*' ]    
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
- name: Retrieve details on all variables for the supplied workspace
  esp.terraform.tfe_workspace_var_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    workspace: bar
    variable:
      - '*'
    validate_certs: no
  register: _result

- name: List workspace variables (supplied by names/keys and IDs)
  esp.terraform.tfe_workspace_var_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    workspace: ws-bLt17oSNcaiGtAuM
    variable:
      - var-sCmHmHGSTYCp38sY
      - AWS_SECRET_ACCESS_KEY
    validate_certs: no
  register: _result
'''

RETURN = r'''
json:
    description: Details on variables.
    returned: success
    type: dict
    contains:
        data:
            description: Details on variables.
            returned: success
            type: list
            elements: dict                    
            sample:
                - attributes:
                      category: env
                      created-at: 2021-04-19T11:39:47.136Z
                      description: null
                      hcl: false
                      key: AWS_SECRET_ACCESS_KEY
                      sensitive: true
                      value: null
                  id: var-SUaLuzd4azmLbB53
                  links:
                      self: /api/v2/workspaces/ws-bLt17oSNcaiGtAuM/vars/var-SUaLuzd4azmLbB53
                  relationships:
                      configurable:
                          data:
                              id: ws-bLt17oSNcaiGtAuM
                              type: workspaces
                          links:
                              related: /api/v2/organizations/foo/workspaces/bar
                  type: vars               
'''

import collections

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_bytes, to_native, to_text

from ansible_collections.esp.terraform.plugins.module_utils.tfe_helper import TFEHelper


def main():
    argument_spec = TFEHelper.tfe_argument_spec()
    argument_spec.update(
        organization=dict(type='str', required=True, no_log=False),
        workspace=dict(type='str', required=True, no_log=False),
        variable=dict(type='list', elements='str', no_log=False, default=[ '*' ]),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,    
    )

    tfe = TFEHelper(module)
    
    organization = tfe.get_org_name_when_exists(organization=module.params['organization'])
    workspace = module.params['workspace']

    # Parse `variable` parameter and create list of variables.
    # It's possible someone passed a comma separated string, so we should handle that.
    # This can be either an empty list or '*' which means all variables.
    variables = module.params['variable']
    if isinstance(module.params['variable'], collections.Iterable):
        variables = [p.strip() for p in module.params['variable']]
        variables = tfe.listify_comma_sep_strings_in_list(variables)
    if not variables:
        variables = [ '*' ]

    # Seed the result dict in the object
    result = dict(
        changed=False,
        organization=organization,
        workspace=workspace,
        variables=variables,
        json={},
    )

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

    if '*' in variables:
        # Retrieve information for all variables
        try:        
            result['json'] = tfe.call_endpoint(tfe.api.workspace_vars.list, workspace_id=workspace_id)
        except Exception as e:
            module.fail_json(msg='Unable to list variables in "%s" workspace. Error: %s.' % (workspace, to_native(e)) )
    else:
        result['json']['data'] = []
        # First, get the list of all variables
        try:        
            all_variables = tfe.call_endpoint(tfe.api.workspace_vars.list, workspace_id=workspace_id)
        except Exception as e:
            module.fail_json(msg='Unable to list variables in "%s" workspace. Error: %s.' % (workspace, to_native(e)) )

        # Next, iterate over the supplied variables to retrieve their details
        for variable in variables:

            # Refer to a variable by its name/key
            if any(v['attributes']['key'] == variable for v in all_variables['data']):
                result['json']['data'].append( [v for v in all_variables['data'] if v['attributes']['key'] == variable][0] )
            # Refer to a variable by its ID
            elif any(v['id'] == variable for v in all_variables['data']):
                result['json']['data'].append( [v for v in all_variables['data'] if v['id'] == variable][0] )
            else:
                module.fail_json(msg='The supplied "%s" variable does not exist in "%s" workspace.' % (variable, workspace) )

    module.exit_json(**result)


if __name__ == '__main__':
    main()