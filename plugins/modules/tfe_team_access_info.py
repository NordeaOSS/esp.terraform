#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Krzysztof Lewandowski <krzysztof.lewandowski@nordea.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: tfe_team_access_info
short_description: List team's permissions on a workspace
description:
- Lists team's permissions on a workspace.
- A team-workspace resource represents a team's local permissions on a specific workspace.
- A single team-workspace resource contains the relationship between the Team and Workspace, including the privileges the team has on the workspace.
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
  team:
    description:
    - List of teams to retrieve permissions for.
    - This can be '*' which means all teams.
    - One may refer to a team either by its ID or its name.
    - One of C(team), C(workspace) or C(relationship) is required.
    type: list
    required: false
  workspace:
    description:
    - List of workspace to retrieve relationships with teams for.
    - This can be '*' which means all workspaces.
    - One may refer to a workspace either by its ID or its name.
    - One of C(team), C(workspace) or C(relationship) is required.
    type: list
    required: false
  relationship:
    description:
    - List of team-workspace resources to retrieve details for.
    - This can be '*' which means all relationships.
    - Refer to a relationship by its ID, i.e. tws-*.
    - One of C(team), C(workspace) or C(relationship) is required.
    type: list
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
- name: List team access to the supplied workspaces
  esp.terraform.tfe_team_access_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    workspace:
      - my-workspace
      - ws-XGA52YVykdTgryTN
      #- '*'
    validate_certs: no
  register: _result

- name: Show team access for the supplied teams
  esp.terraform.tfe_team_access_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    team:
      - developers
      - team-EhuyjdMvkUaLLMEd
      #- '*'
    validate_certs: no
  register: _result

- name: Show a team access relationship
  esp.terraform.tfe_team_access_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    relationship:
      - tws-19iugLwoNgtWZbKP
      #- '*'
    validate_certs: no
  register: _result
'''

RETURN = r'''
json:
    description: Details on teams access.
    returned: success
    type: dict
    contains:
        data:
            description: Details on team access.
            returned: success
            type: list
            elements: dict                    
            sample:
                - attributes:
                      access: plan
                      runs: plan
                      sentinel-mocks: none
                      state-versions: read
                      variables: read
                      workspace-locking: false
                  id: tws-P6ehPeR96ngzRtep
                  links:
                      self: /api/v2/team-workspaces/tws-P6ehPeR96ngzRtep
                  relationships:
                      team:
                          data:
                              id: team-EhuyjdMvkUaLLMEd
                              type: teams
                          links:
                              related: /api/v2/teams/team-EhuyjdMvkUaLLMEd
                      workspace:
                          data:
                              id: ws-upBS5wz93fDhtwpn
                              type: workspaces
                          links:
                              related: /api/v2/organizations/esp-api-test/workspaces/my-workspace
                  type: team-workspaces               
'''

import collections

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_bytes, to_native, to_text

from ansible_collections.esp.terraform.plugins.module_utils.tfe_helper import TFEHelper


def main():
    argument_spec = TFEHelper.tfe_argument_spec()
    argument_spec.update(
        organization=dict(type='str', required=True, no_log=False),
        team=dict(type='list', elements='str', no_log=False, required=False),
        workspace=dict(type='list', elements='str', no_log=False, required=False),
        relationship=dict(type='list', elements='str', no_log=False, required=False),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[('team', 'workspace', 'relationship')],
        mutually_exclusive=[('team', 'workspace', 'relationship')]
    )

    tfe = TFEHelper(module)
    
    organization = tfe.get_org_name_when_exists(organization=module.params['organization'])

    # Parse `team` parameter and create list of teams.
    teams = module.params['team']
    if isinstance(module.params['team'], collections.Iterable):
        teams = [p.strip() for p in module.params['team']]
        teams = tfe.listify_comma_sep_strings_in_list(teams)

    # Parse `workspace` parameter and create list of workspaces.
    workspaces = module.params['workspace']
    if isinstance(module.params['workspace'], collections.Iterable):
        workspaces = [p.strip() for p in module.params['workspace']]
        workspaces = tfe.listify_comma_sep_strings_in_list(workspaces)

    # Parse `relationship` parameter and create list of relationships.
    relationships = module.params['relationship']
    if isinstance(module.params['relationship'], collections.Iterable):
        relationships = [p.strip() for p in module.params['relationship']]
        relationships = tfe.listify_comma_sep_strings_in_list(relationships)

    # Seed the result dict in the object
    result = dict(
        changed=False,
        organization=organization,
        json={},
    )
    if teams is not None:
        result['teams'] = teams
    if workspaces is not None:
        result['workspaces'] = workspaces
    if relationships is not None:
        result['relationships'] = relationships

    result['json']['data'] = []

    # Set organization
    try:        
        tfe.call_endpoint(tfe.api.set_org, org_name=organization)
    except Exception as e:
        module.fail_json(msg='Unable to set "%s" organization to use for org specific endpoints: %s' % (organization, to_native(e)))
    
    # Retrieve information for all workspaces
    try:        
        all_workspaces = tfe.call_endpoint(tfe.api.workspaces.list_all, include=None)
    except Exception as e:
        module.fail_json(msg='Unable to list workspaces in "%s" organization. Error: %s.' % (organization, to_native(e)) )
    all_workspaces_ids = [w['id'] for w in all_workspaces['data']]

    if relationships is not None:

        if '*' in relationships:
            filters = []
            for workspace in all_workspaces_ids:
                filters.append({ "keys": ["workspace", "id"], "value": workspace })

            for filter in filters:
                try:        
                    result['json']['data'].extend( tfe.call_endpoint(tfe.api.team_access.list, filters=[ filter ])['data'] )
                except Exception as e:
                    module.fail_json(msg='Unable to retrieve team access in "%s" organization. Error: %s.' % (organization, to_native(e)) )
        else:
            # Retrieve information for all relationships
            for relationship in relationships:
                try:        
                    result['json']['data'].append( tfe.call_endpoint(tfe.api.team_access.show, access_id=relationship)['data'] )
                except Exception as e:
                    module.fail_json(msg='Unable to retrieve "%s" team-relationship in "%s" organization. Error: %s.' % (relationship, organization, to_native(e)) )

    if workspaces is not None:

        if '*' in workspaces:
            workspaces = all_workspaces_ids

        filters = []
        for workspace in workspaces:            
            matching_workspace = [w for w in all_workspaces['data'] if w['attributes']['name'] == workspace or w['id'] == workspace]            
            if len(matching_workspace) == 1:
                workspace_id = matching_workspace[0]['id']
                filters.append({ "keys": ["workspace", "id"], "value": workspace_id })

        for filter in filters:
            try:        
                result['json']['data'].extend( tfe.call_endpoint(tfe.api.team_access.list, filters=[ filter ])['data'] )
            except Exception as e:
                module.fail_json(msg='Unable to retrieve team access in "%s" organization. Error: %s.' % (organization, to_native(e)) )

    if teams is not None:

        filters = []
        for workspace in all_workspaces_ids:
            filters.append({ "keys": ["workspace", "id"], "value": workspace })

        if len(filters) > 0:
            ret = []
            for filter in filters:
                try:        
                    ret.extend( tfe.call_endpoint(tfe.api.team_access.list, filters=[ filter ])['data'] )
                except Exception as e:
                    module.fail_json(msg='Unable to retrieve team access in "%s" organization. Error: %s.' % (organization, to_native(e)) )

            if '*' in teams:
                result['json']['data'] = ret

            else:
                # Retrieve information for all teams
                try:        
                    all_teams = tfe.call_endpoint(tfe.api.teams.list_all, include=None)
                except Exception as e:
                    module.fail_json(msg='Unable to list teams in "%s" organization. Error: %s.' % (organization, to_native(e)) )

                for team in teams:
                    matching_team = [t for t in all_teams['data'] if t['attributes']['name'] == team or t['id'] == team]

                    if len(matching_team) == 1:
                        team_id = matching_team[0]['id']
                        matching_access = [a for a in ret if a['relationships']['team']['data']['id'] == team_id]
                        result['json']['data'].extend( matching_access )
                    else:
                        module.fail_json(msg='Team "%s" does not exist in "%s" organization,' % (team, organization) )

    module.exit_json(**result)


if __name__ == '__main__':
    main()