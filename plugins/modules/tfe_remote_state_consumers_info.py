#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Krzysztof Lewandowski <krzysztof.lewandowski@nordea.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: tfe_remote_state_consumers_info
short_description: List Remote State Consumers for a given workspace
description:
- Retrieves the list of other workspaces that are allowed to access the given workspace's state during runs.
- A workspace may be referred either by its id or its name.
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
    - The Workspace name or ID.
    type: str
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
- name: Get Remote State Consumers
  esp.terraform.tfe_remote_state_consumers_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    workspace: my-workspace
    validate_certs: no
  register: _result
'''

RETURN = r'''
organization:
    description: Organization name or external-id.
    returned: always
    type: str
    sample: foo
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
                      name: my-workspace-2
                      locked: false
                      execution-mode: remote
                  id: ws-c4QU38B37cuh873N
                  type: workspaces                 
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_bytes, to_native, to_text

from ansible_collections.esp.terraform.plugins.module_utils.tfe_helper import TFEHelper


def main():
    argument_spec = TFEHelper.tfe_argument_spec()
    argument_spec.update(
        organization=dict(type='str', required=True, no_log=False),
        workspace=dict(type='str', required=True, no_log=False),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,    
    )

    tfe = TFEHelper(module)

    organization = tfe.get_org_name_when_exists(organization=module.params['organization'])
    workspace = module.params['workspace']

    # Seed the result dict in the object
    result = dict(
        changed=False,
        organization=organization,
        workspace=workspace,
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

    try:        
        #result['json'] = tfe.call_endpoint(tfe.api.workspaces.get_remote_state_consumers, workspace_id=workspace_id)
        #result['json'] = tfe.call_endpoint(tfe.api.workspaces._get, url=tfe.TFE_URL + "/api/v2/workspaces/" + workspace_id + "/relationships/remote-state-consumers")
        result['json'] = tfe.call_endpoint(tfe.api.workspaces._list_all, url=tfe.TFE_URL + "/api/v2/workspaces/" + workspace_id + "/relationships/remote-state-consumers")
    except Exception as e:
        module.fail_json(msg='Unable to retrieve details on Remote State Consumers in "%s" workspace. Error: %s.' % (workspace, to_native(e)) )

    module.exit_json(**result)


if __name__ == '__main__':
    main()