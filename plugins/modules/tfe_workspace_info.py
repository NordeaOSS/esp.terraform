#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Krzysztof Lewandowski <krzysztof.lewandowski@nordea.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: tfe_workspace_info
short_description: List workspaces in the organization
description:
- Lists workspaces in the organization.
- Workspaces represent running infrastructure managed by Terraform.
- Details on a workspace can be retrieved either by its ID or by its name.
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
    - List of workspaces to retrieve details for.
    - This can be '*' which means all workspaces.
    - One may refer to a workspace either by its ID or its name.
    type: list
    required: false
    default: [ '*' ]
  include:
    description:
    - Return additional information about nested resources.
    - This can be any of organization, current_run, current_run.plan, current_run.configuration_version, current_run.configuration_version.ingress_attributes, readme, outputs.
    type: list
    elements: str
    required: false
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
- name: Retrieve details on all workspaces in the organization, include additional information about current run and outputs
  esp.terraform.tfe_workspace_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    workspace:
      - '*'
    include:
      - current_run
      - outputs
    validate_certs: no
  register: _result

- name: Retrieve details on given workspaces (supplied by names or IDs), do not include any additional information
  esp.terraform.tfe_workspace_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    workspace:
      - ws-bLt17oSNcaiGtAuM
      - my_test_workspace
    validate_certs: no
  register: _result
'''

RETURN = r'''
organization:
    description: Organization name or external-id.
    returned: always
    type: str
    sample: foo
workspace:
    description: List of workspaces to retrieve details for.
    returned: always
    type: list
    elements: dict
    sample:
        - ws-bLt17oSNcaiGtAuM
        - my_test_workspace
json:
    description: Details on workspaces.
    returned: success
    type: dict
    contains:
        data:
            description: Details on workspaces.
            returned: success
            type: list
            elements: dict            
            sample:
                - attributes:
                      name: my_test_workspace
                      locked: false
                      execution-mode: remote
                  id: ws-c4QU38B37cuh873N
                  type: workspaces                 
        included:
            description: Additional information about nested resources.
            returned: success
            type: list
            elements: dict 
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_bytes, to_native, to_text

from ansible_collections.esp.terraform.plugins.module_utils.tfe_helper import TFEHelper


def main():
    argument_spec = TFEHelper.tfe_argument_spec()
    argument_spec.update(
        organization=dict(type='str', required=True, no_log=False),
        workspace=dict(type='list', elements='str', no_log=False, default=[ '*' ]),
        include=dict(type='list', elements='str', no_log=False, required=False, choices=['organization', 'current_run', 'current_run.plan', 'current_run.configuration_version', 'current_run.configuration_version.ingress_attributes', 'readme', 'outputs']),        
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,    
    )

    tfe = TFEHelper(module)

    organization = tfe.get_org_name_when_exists(organization=module.params['organization'])
    include = module.params['include']

    # Parse `workspace` parameter and create list of workspaces.
    # It's possible someone passed a comma separated string, so we should handle that.
    # This can be either an empty list or '*' which means all workspaces.
    workspaces = []
    workspaces = [p.strip() for p in module.params['workspace']]
    workspaces = tfe.listify_comma_sep_strings_in_list(workspaces)
    if not workspaces:
        workspaces = [ '*' ]

    # Seed the result dict in the object
    result = dict(
        changed=False,
        organization=organization,
        workspaces=workspaces,
        json={},
    )

    # Set organization
    try:        
        tfe.call_endpoint(tfe.api.set_org, org_name=organization)
    except Exception as e:
        module.fail_json(msg='Unable to set "%s" organization to use for org specific endpoints: %s' % (organization, to_native(e)))
    
    if '*' in workspaces:
        # Retrieve information for all workspaces
        try:        
            result['json'] = tfe.call_endpoint(tfe.api.workspaces.list_all, include=include)
        except Exception as e:
            module.fail_json(msg='Unable to list workspaces in "%s" organization. Error: %s.' % (organization, to_native(e)) )
    else:
        result['json']['data'] = []
        result['json']['included'] = []
        # First, get the list of all workspaces without additional details
        try:        
            all_workspaces = tfe.call_endpoint(tfe.api.workspaces.list_all, include=None)
        except Exception as e:
            module.fail_json(msg='Unable to list workspaces in "%s" organization. Error: %s.' % (organization, to_native(e)) )

        # Next, iterate over the supplied workspaces to retrieve their details
        for workspace in workspaces:

            # Refer to a workspace by its name
            if any(w['attributes']['name'] == workspace for w in all_workspaces['data']):
                try:        
                    ret = tfe.call_endpoint(tfe.api.workspaces.show, workspace_name=workspace, include=include)
                except Exception as e:
                    module.fail_json(msg='Unable to retrieve details on a workspace in "%s" organization. Error: %s.' % (organization, to_native(e)) )

            # Refer to a workspace by its ID
            else:
                try:        
                    ret = tfe.call_endpoint(tfe.api.workspaces.show, workspace_id=workspace, include=include)
                except Exception as e:
                    module.fail_json(msg='Unable to retrieve details on a workspace in "%s" organization. Error: %s.' % (organization, to_native(e)) )

            result['json']['data'].append(ret['data'])
            if include is not None:
                result['json']['included'].extend(ret['included'])            

    module.exit_json(**result)


if __name__ == '__main__':
    main()