#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Krzysztof Lewandowski <krzysztof.lewandowski@nordea.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: tfe_state_version_info
short_description: List State Versions for a Workspace
description:
- Lists State Versions for a Workspace.
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
    - The Workspace name or ID to list State Versions for.
    type: str
    required: true    
  state_version:
    description:
    - List of State Versions to retrieve details for (supplied by state version IDs).
    - This can be '*' which means all State Versions.
    - C(current-state-version) means fetch the Current State Version for the Workspace.
    type: list
    required: false
    default: [ '*' ]
  include:
    description:
    - Return additional information about nested resources.
    - This can be only C(outputs) as of now.
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
- name: List all State Versions for a Workspace
  esp.terraform.tfe_state_version_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    workspace: bar
    state_version:
      - '*'
    validate_certs: no
  register: _result

- name: Fetch the Current State Version for a Workspace, include outputs
  esp.terraform.tfe_state_version_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    workspace: bar
    state_version:
      - current-state-version
    include:
      - outputs
    validate_certs: no
  register: _result

- name: List State Versions for a Workspace (state versions supplied by IDs), include outputs
  esp.terraform.tfe_state_version_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    workspace: ws-bLt17oSNcaiGtAuM
    state_version:
      - sv-4mXRs55FUQVWV4eG
      - sv-rGAoW3w4zYhQxWtW
    include:
      - outputs      
    validate_certs: no
  register: _result
'''

RETURN = r'''
json:
    description: Details on state versions.
    returned: success
    type: dict
    contains:
        data:
            description: Details on state versions.
            returned: success
            type: list
            elements: dict                    
            sample:
                - attributes:
                      created-at: 2021-04-19T11:49:36.271Z
                      hosted-state-download-url: 'https://terraform.example.com/_archivist/v1/object/dm...'
                      modules:
                          root.ec2:
                              aws-instance: 1
                      providers:
                          provider[\registry.terraform.io/hashicorp/aws\]:
                              aws-instance: 1
                      resources:
                          - count: 1
                            module: root.ec2
                            name: this
                            provider: provider[\registry.terraform.io/hashicorp/aws\]
                            type: aws_instance
                      serial: 0
                      size: 1563
                      state-version: 4
                      terraform-version: 0.13.6
                      vcs-commit-sha: e136364b2c11678e18cbc57e3ab11d3e832a6afa
                      vcs-commit-url: https://bitbucket.example.com/projects/BAZ/repos/qux/commits/e136364b2c11678e18cbc57e3ab11d3e832a6afa
                  id: sv-RiiBKNQXSvG83YWB
                  links:
                      self: /api/v2/state-versions/sv-RiiBKNQXSvG83YWB
                  relationships:
                      created-by:
                          data:
                              id: user-xNvjG1FhNtYb3RfA
                              type: users
                          links:
                              related: /api/v2/runs/sv-RiiBKNQXSvG83YWB/created-by
                      outputs:
                          data:
                              - id: wsout-yYP8gVfCFhBKoK7m
                                type: state-version-outputs
                              - id: wsout-Ve2aH5dZBCknfFjU
                                type: state-version-outputs
                      run:
                          data:
                              id: run-H5LEQGwanGc4YQJN
                              type: runs
                  type: state-versions             
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
        state_version=dict(type='list', elements='str', no_log=False, default=[ '*' ]),
        include=dict(type='list', elements='str', no_log=False, required=False, choices=['outputs']), 
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,    
    )

    tfe = TFEHelper(module)
    
    organization = tfe.get_org_name_when_exists(organization=module.params['organization'])
    workspace = module.params['workspace']
    include = module.params['include']

    # Parse `state_version` parameter and create list of State Versions.
    # It's possible someone passed a comma separated string, so we should handle that.
    # This can be either an empty list or '*' which means all State Versions.
    state_versions = module.params['state_version']
    if isinstance(module.params['state_version'], collections.Iterable):
        state_versions = [p.strip() for p in module.params['state_version']]
        state_versions = tfe.listify_comma_sep_strings_in_list(state_versions)
    if not state_versions:
        state_versions = [ '*' ]

    # Seed the result dict in the object
    result = dict(
        changed=False,
        organization=organization,
        workspace=workspace,
        state_versions=state_versions,
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

    # Seed the filters list
    filters = [
        {
            "keys": ["workspace", "name"],
            "value": [w for w in all_workspaces['data'] if w['id'] == workspace_id][0]['attributes']['name']
        },
        {
            "keys": ["organization", "name"],
            "value": organization
        }
    ]

    if '*' in state_versions:
        # Retrieve information for all State Versions
        try:        
            result['json'] = tfe.call_endpoint(tfe.api.state_versions.list_all, filters=filters, include=include)
        except Exception as e:
            module.fail_json(msg='Unable to list state versions for "%s" workspace. Error: %s.' % (workspace, to_native(e)) )

    elif 'current-state-version' in state_versions:
        # Fetch the Current State Version for a Workspace
        try:        
            result['json'] = tfe.call_endpoint(tfe.api.state_versions.get_current, workspace_id=workspace_id, include=include)
        except Exception as e:
            module.fail_json(msg='Unable to fetch current state version for "%s" workspace. Error: %s.' % (workspace, to_native(e)) )

    else:
        result['json']['data'] = []
        result['json']['included'] = []

        # Iterate over the supplied state versions to retrieve their details
        for state_version_id in state_versions:

            try:        
                ret = tfe.call_endpoint(tfe.api.state_versions.show, state_version_id=state_version_id, include=include)
            except Exception as e:
                module.fail_json(msg='Unable to show "%s" state version for "%s" workspace. Error: %s.' % (state_version_id, workspace, to_native(e)) )

            result['json']['data'].append(ret['data'])
            if include is not None:
                result['json']['included'].extend(ret['included'])  

    module.exit_json(**result)


if __name__ == '__main__':
    main()