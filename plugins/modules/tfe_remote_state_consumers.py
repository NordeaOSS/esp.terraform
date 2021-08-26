#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Krzysztof Lewandowski <krzysztof.lewandowski@nordea.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: tfe_remote_state_consumers
short_description: Add, delete, or replace one or more remote state consumers from a workspace
description:
- Adds, deletes, or replaces one or more remote state consumers from a workspace.
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
    - A Workspace to add/delete/replace remote state consumers to.
    - One may refer to a workspace either by its ID or its name.
    type: str
    required: true
  remote_state_consumer:
    description:
    - List of workspaces to add/delete/replace as Remote State Consumers to C(workspace).
    - This can be '*' which means all workspaces in the organization.
    - One may refer to a workspace either by its ID or its name.
    type: list
    required: false
    default: [ '*' ]
  action:
    description:
    - When C(add), it adds one or more remote state consumers to the workspace, according to the contents of C(remote_state_consumers) parameter.
    - You can safely add a consumer workspace that is already present; it will be ignored, and the rest of the consumers in the request will be processed normally.
    - When C(delete), it removes one or more remote state consumers from a workspace, according to the contents of C(remote_state_consumers) parameter.
    - When C(replace), it updates the workspace's remote state consumers to be exactly the list of workspaces specified in C(remote_state_consumers).
    type: str
    default: add
    choices: [ add, delete, replace ]
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
- name: Add remote state consumers to a workspace
  esp.terraform.tfe_remote_state_consumers:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    workspace: my-workspace
    remote_state_consumer:
      - '*'   
    action: add
    validate_certs: no

- name: Update the workspace's remote state consumers to be exactly the list of remote_state_consumer specified
  esp.terraform.tfe_remote_state_consumers:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    workspace: my-workspace
    remote_state_consumer:
      - ws-bLt17oSNcaiGtAuM
      - my-workspace-2    
    action: replace
    validate_certs: no

- name: Remove remote state consumers from a workspace
  esp.terraform.tfe_remote_state_consumers:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    workspace: my-workspace
    remote_state_consumer:
      - my-workspace-2  
    action: delete
    validate_certs: no
'''

RETURN = r'''
organization:
    description: Organization name or external-id.
    returned: always
    type: str
    sample: foo
workspace:
    description: A Workspace to add/delete/replace remote state consumers to.
    returned: always
    type: str
    sample: my-workspace 
remote_state_consumers:
    description: List of workspaces to add/delete/replace as Remote State Consumer
    returned: always
    type: list
    elements: dict
    sample:
        - ws-bLt17oSNcaiGtAuM
        - my-workspace-2       
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
        remote_state_consumer=dict(type='list', elements='str', no_log=False, default=[ '*' ]), 
        action=dict(type='str', choices=['add', 'delete', 'replace'], default='add'),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,  
    )

    tfe = TFEHelper(module)

    organization = tfe.get_org_name_when_exists(organization=module.params['organization'])
    workspace = module.params['workspace']
    action = module.params['action']

    # Parse `remote_state_consumer` parameter and create list of Remote State Consumers.
    # It's possible someone passed a comma separated string, so we should handle that.
    # This can be either an empty list or '*' which means all Remote State Consumers.
    remote_state_consumers = module.params['remote_state_consumer']
    if isinstance(module.params['remote_state_consumer'], collections.Iterable):
        remote_state_consumers = [p.strip() for p in module.params['remote_state_consumer']]
        remote_state_consumers = tfe.listify_comma_sep_strings_in_list(remote_state_consumers)
    if not remote_state_consumers:
        remote_state_consumers = [ '*' ]

    # Seed the result dict in the object
    result = dict(
        changed=False,
        action=action,
        organization=organization,
        workspace=workspace,
        remote_state_consumers=remote_state_consumers,
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

    # Build Remote State Consumers payload data
    remote_state_consumers_data_payload = []
    remote_state_consumers_ids = []
    if '*' in remote_state_consumers:
        for w in all_workspaces['data']:
            if w['id'] != workspace_id:
                remote_state_consumers_data_payload.append({ "id": w['id'], "type": "workspaces"})
                remote_state_consumers_ids.append(w['id'])

    else:
        for rsc in remote_state_consumers:
            # Refer to a workspace by its name
            if any(w['attributes']['name'] == rsc for w in all_workspaces['data']):
                rsc_id = [w for w in all_workspaces['data'] if w['attributes']['name'] == rsc][0]['id']
            # Refer to a workspace by its ID
            elif any(w['id'] == rsc for w in all_workspaces['data']):
                rsc_id = rsc
            else:
                module.fail_json(msg='The supplied "%s" workspace does not exist in "%s" organization.' % (rsc, organization) )

            if rsc_id != workspace_id:
                remote_state_consumers_data_payload.append({ "id": rsc_id, "type": "workspaces"})
                remote_state_consumers_ids.append(rsc_id)

    rsc_payload = {
      "data": remote_state_consumers_data_payload
    }

    # Get the list of current Remote State Consumers for the supplied workspace
    try:        
        current_remote_state_consumers = tfe.call_endpoint(tfe.api.workspaces._list_all, url=tfe.TFE_URL + "/api/v2/workspaces/" + workspace_id + "/relationships/remote-state-consumers")
    except Exception as e:
        module.fail_json(msg='Unable to retrieve details on Remote State Consumers in "%s" workspace. Error: %s.' % (workspace, to_native(e)) )
    current_remote_state_consumers_ids = [w['id'] for w in current_remote_state_consumers['data']]

    # Add Remote State Consumers
    if action == 'add':

        # Check if 'remote_state_consumers_ids' is a subset of 'current_remote_state_consumers_ids', i.e. if there is any change
        if not tfe.is_subset(subset=remote_state_consumers_ids, superset=current_remote_state_consumers_ids):

            if not module.check_mode:
                try:        
                    #result['json'] = tfe.call_endpoint(tfe.api.workspaces.add_remote_state_consumers, workspace_id=workspace_id, payload=rsc_payload)
                    result['json'] = tfe.call_endpoint(tfe.api.workspaces._post, url=tfe.TFE_URL + "/api/v2/workspaces/" + workspace_id + "/relationships/remote-state-consumers", data=rsc_payload)
                except Exception as e:
                    module.fail_json(msg='Unable to add Remote State Consumers to "%s" workspace in "%s" organization. Error: %s.' % (workspace, organization, to_native(e)) )          

            result['changed'] = True

    # Replace Remote State Consumers
    if action == 'replace':

        # Check if 'remote_state_consumers_ids' is the same as 'current_remote_state_consumers_ids', i.e. if there is any change
        if not remote_state_consumers_ids == current_remote_state_consumers_ids:

            if not module.check_mode:
                try:        
                    #result['json'] = tfe.call_endpoint(tfe.api.workspaces.replace_remote_state_consumers, workspace_id=workspace_id, payload=rsc_payload)
                    result['json'] = tfe.call_endpoint(tfe.api.workspaces._patch, url=tfe.TFE_URL + "/api/v2/workspaces/" + workspace_id + "/relationships/remote-state-consumers", data=rsc_payload)
                except Exception as e:
                    module.fail_json(msg='Unable to replace Remote State Consumers in "%s" workspace in "%s" organization. Error: %s.' % (workspace, organization, to_native(e)) )          

            result['changed'] = True

    # Delete Remote State Consumers
    if action == 'delete':

        # Check if 'remote_state_consumers_ids' is a subset of 'current_remote_state_consumers_ids', i.e. if there is any change
        if tfe.is_subset(subset=remote_state_consumers_ids, superset=current_remote_state_consumers_ids):

            if not module.check_mode:
                try:        
                    #result['json'] = tfe.call_endpoint(tfe.api.workspaces.delete_remote_state_consumers, workspace_id=workspace_id, payload=rsc_payload)
                    result['json'] = tfe.call_endpoint(tfe.api.workspaces._delete, url=tfe.TFE_URL + "/api/v2/workspaces/" + workspace_id + "/relationships/remote-state-consumers", data=rsc_payload)
                except Exception as e:
                    module.fail_json(msg='Unable to delete Remote State Consumers from "%s" workspace in "%s" organization. Error: %s.' % (workspace, organization, to_native(e)) )          

            result['changed'] = True

    module.exit_json(**result)


if __name__ == '__main__':
    main()