#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Krzysztof Lewandowski <krzysztof.lewandowski@nordea.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: tfe_team_access
short_description: Add, update or remove team access to a workspace
description:
- Adds, updates or removes team access to a workspace.
- Teams and workspaces may be referred either by their ids or their names.
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
    - The ID or name of the team to add to the workspace, or remove from the workspace.
    type: str
    required: false    
  workspace:
    description:
    - The workspace name or ID to which the team is to be added or removed.
    type: str
    required: false
  relationship:
    description:
    - The ID of the team/workspace relationship to remove.
    - Applicable only when C(state=absent).
    - Alternatively use C(team) and C(workspace) options if you don't know relationship ID.
    type: str
    required: false  
  attributes:
    description:
    - Definition of the access properties.
    - Required when C(state=present).       
    type: dict
    required: false      
    suboptions:
      access:
        description:
        - The type of access to grant.
        type: str
        choices: [ read, plan, write, admin, custom ]
        required: true
      runs:
        description:
        - If access is custom, the permission to grant for the workspace's runs. Can only be used when C(access=custom).
        type: str
        choices: [ read, plan, apply ]
        required: false 
      variables:
        description:
        - If access is custom, the permission to grant for the workspace's variables. Can only be used when C(access=custom).
        type: str
        choices: [ none, read, write ]
        required: false
      state-versions:
        description:
        - If access is custom, the permission to grant for the workspace's state versions. Can only be used when C(access=custom).
        type: str
        choices: [ none, read-outputs, read, write ]
        required: false
      sentinel-mocks:
        description:
        - If access is custom, the permission to grant for the workspace's Sentinel mocks. Can only be used when C(access=custom).
        type: str
        choices: [ none, read ]
        required: false
      workspace-locking:
        description:
        - If access is custom, the permission granting the ability to manually lock or unlock the workspace. Can only be used when C(access=custom).
        type: bool
        required: false
  state:
    description:
    - Whether the team access should exist or not.
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
- name: Add or update Team access to a Workspace
  esp.terraform.tfe_team_access:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    team: developers
    workspace: my-workspace
    attributes:
      "access": custom
      "runs": apply
      "variables": none
      "state-versions": read-outputs
      "sentinel-mocks": read
      "workspace-locking": false
    state: present
    validate_certs: no

- name: Remove Team access to a Workspace
  esp.terraform.tfe_team_access:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    team: developers
    workspace: my-workspace
    state: absent
    validate_certs: no
'''

RETURN = r'''
json:
    description: Details on the team access.
    returned: success
    type: dict
    contains:
        data:
            description: Details on the team access.
            returned: success
            type: dict                  
            sample:
                attributes:
                    access: custom
                    runs: apply
                    sentinel-mocks: read
                    state-versions: read-outputs
                    variables: none
                    workspace-locking: false
                id: tws-qj8ugVEZLV9JsLLw
                links:
                    self: /api/v2/team-workspaces/tws-qj8ugVEZLV9JsLLw
                relationships:
                    team:
                        data:
                            id: team-EMyKbSwR3FbgpDop
                            type: teams
                        links:
                            related: /api/v2/teams/team-EMyKbSwR3FbgpDop
                    workspace:
                        data:
                            id: ws-upBS5wz93fDhtwpn
                            type: workspaces
                        links:
                            related: /api/v2/organizations/foo/workspaces/my-workspace
                type: team-workspaces          
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_bytes, to_native, to_text

from ansible_collections.esp.terraform.plugins.module_utils.tfe_helper import TFEHelper


def main():
    argument_spec = TFEHelper.tfe_argument_spec()
    argument_spec.update(
        organization=dict(type='str', required=True, no_log=False),      
        team=dict(type='str', required=False, no_log=False),
        workspace=dict(type='str', required=False, no_log=False),
        relationship=dict(type='str', required=False, no_log=False),
        state=dict(type='str', choices=['present', 'absent'], default='present'),
        attributes=dict(
            type='dict', 
            required=False, no_log=False,
        )
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,  
        mutually_exclusive=[('relationship', 'team'), ('relationship', 'workspace')],
        required_together=[('team', 'workspace')],
        required_if=[('state', 'absent', ('relationship', 'team'), True), ('state', 'present', ('attributes',), False), ('state', 'present', ('relationship', 'team'), True)],        
    )

    tfe = TFEHelper(module)

    organization = tfe.get_org_name_when_exists(organization=module.params['organization'])
    team = module.params['team']
    workspace = module.params['workspace']
    relationship = module.params['relationship']
    state = module.params['state']
    attributes = module.params['attributes']

    # Seed the result dict in the object
    result = dict(
        changed=False,
        state=state,
        organization=organization,
        json={},
    )
    if team is not None:
        result['team'] = team
    if workspace is not None:
        result['workspace'] = workspace
    if relationship is not None:
        result['relationship'] = relationship                
    if attributes is not None:
        result['attributes'] = attributes

    # Set organization
    try:        
        tfe.call_endpoint(tfe.api.set_org, org_name=organization)
    except Exception as e:
        module.fail_json(msg='Unable to set "%s" organization to use for org specific endpoints: %s' % (organization, to_native(e)))

    # Get the list of all teams
    try:        
        all_teams = tfe.call_endpoint(tfe.api.teams.list_all, include=None)
    except Exception as e:
        module.fail_json(msg='Unable to list teams in "%s" organization. Error: %s.' % (organization, to_native(e)) )

    # Get the team ID. 
    team_id = None
    if team is not None:
    # Refer to a team by its name
        if any(t['attributes']['name'] == team for t in all_teams['data']):
            team_id = [t for t in all_teams['data'] if t['attributes']['name'] == team][0]['id']
        elif any(t['id'] == team for t in all_teams['data']):
            team_id = team
        else:
            module.fail_json(msg='The supplied "%s" team does not exist in "%s" organization.' % (team, organization) )

    # Get the list of all workspaces
    try:        
        all_workspaces = tfe.call_endpoint(tfe.api.workspaces.list_all, include=None)
    except Exception as e:
        module.fail_json(msg='Unable to list workspaces in "%s" organization. Error: %s.' % (organization, to_native(e)) )

    # Get the workspace ID. 
    workspace_id = None
    if workspace is not None:
    # Refer to a team by its name
        if any(w['attributes']['name'] == workspace for w in all_workspaces['data']):
            workspace_id = [w for w in all_workspaces['data'] if w['attributes']['name'] == workspace][0]['id']
        elif any(w['id'] == workspace for w in all_workspaces['data']):
            workspace_id = workspace
        else:
            module.fail_json(msg='The supplied "%s" workspace does not exist in "%s" organization.' % (workspace, organization) )

    # Get the list of all relationships
    filters = []
    all_relationships = dict( data=[] )
    for workspace_item in all_workspaces['data']:
        filters.append({ "keys": ["workspace", "id"], "value": workspace_item['id'] })    
    for filter in filters:
        try:        
            all_relationships['data'].extend( tfe.call_endpoint(tfe.api.team_access.list, filters=[ filter ])['data'] )
        except Exception as e:
            module.fail_json(msg='Unable to retrieve team access in "%s" organization. Error: %s.' % (organization, to_native(e)) )

    # Verify the relationship ID.
    if relationship is not None:
        if not any(r['id'] == relationship for r in all_relationships['data']):
            module.fail_json(msg='The supplied "%s" relationship does not exist in "%s" organization.' % (relationship, organization) )

    if relationship is None:
        matching_relationships = [r for r in all_relationships['data'] if r['relationships']['team']['data']['id'] == team_id and r['relationships']['workspace']['data']['id'] == workspace_id]
        if len(matching_relationships) > 0:
            relationship = matching_relationships[0]['id']

    # Remove the team access if it exists and state == 'absent'
    if state == 'absent':

        if relationship is not None:
            if not module.check_mode:
                try:        
                    result['json'] = tfe.call_endpoint(tfe.api.team_access.remove_team_access, access_id=relationship)
                except Exception as e:
                    module.fail_json(msg='Unable to remove "%s" team access in "%s" organization. Error: %s.' % (relationship, organization, to_native(e)) )          

            result['changed'] = True
 
    # Update the team access if it exists and state == 'present'
    if (state == 'present') and (relationship is not None):

        if attributes is not None:
            r_payload = {
              "data": {
                "attributes": attributes
              }
            }

            # Check if 'attributes' is a subset of current attributes, i.e. if there is any change
            current_attributes = [r for r in all_relationships['data'] if r['id'] == relationship][0]['attributes']            
            if not tfe.is_subset(subset=attributes, superset=current_attributes):

                if not module.check_mode:
                    try:        
                        result['json'] = tfe.call_endpoint(tfe.api.team_access.update, access_id=relationship, payload=r_payload)
                    except Exception as e:
                        module.fail_json(msg='Unable to update "%s" team access in "%s" organization. Error: %s.' % (relationship, organization, to_native(e)) )          

                result['changed'] = True

    # Add the team access if it does not exist and state == 'present'
    if (state == 'present') and (relationship is None):

        r_payload = {
          "data": {
            "attributes": attributes,
            "relationships": {
              "workspace": {
                "data": {
                  "type": "workspaces",
                  "id": workspace_id
                }
              },
              "team": {
                "data": {
                  "type": "teams",
                  "id": team_id
                }
              }
            },
            "type": "team-workspaces"
          }
        }

        if not module.check_mode:
            try:        
                result['json'] = tfe.call_endpoint(tfe.api.team_access.add_team_access, payload=r_payload)
            except Exception as e:
                module.fail_json(msg='Unable to add team access in "%s" organization. Error: %s.' % (organization, to_native(e)) )          

        result['changed'] = True


    module.exit_json(**result)


if __name__ == '__main__':
    main()