#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Krzysztof Lewandowski <krzysztof.lewandowski@nordea.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: tfe_organization
short_description: Create, update, and destroy organizations
description:
- Creates, updates or removes Terraform organizations.
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
    - Organization name to update or remove.
    - Required when C(state=absent).     
    type: str
    required: false    
  attributes:
    description:
    - Definition of the organization properties.
    - Required when C(state=present).       
    type: dict
    required: false      
    suboptions:
      name:
        description:
        - Name of the organization.
        type: str
        required: true    
      email:
        description:
        - Admin email address.
        type: str
        required: true
      session-timeout:
        description:
        - Session timeout after inactivity (minutes).
        type: int
        required: false
      session-remember:
        description:
        - Session expiration (minutes). 
        type: int
        required: false
      collaborator-auth-policy:
        description:
        - Authentication policy (password or two_factor_mandatory).
        type: str
        required: false
      cost-estimation-enabled:
        description:
        - Whether or not the cost estimation feature is enabled for all workspaces in the organization.
        type: bool
        required: false 
      owners-team-saml-role-id:
        description:
        - Optional. SAML only The name of the owners team.
        type: str
        required: false                       
  state:
    description:
    - Whether the organization should exist or not.
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
- name: Create or update an Organization
  esp.terraform.tfe_organization:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    attributes:
      "name": foo
      "email": jsmith@example.com
      "session-timeout": 20160
      "session-remember": 20160
      "collaborator-auth-policy": password
      "cost-estimation-enabled": true
      #"owners-team-saml-role-id": owners
    state: present
    validate_certs: no

- name: Destroy an Organization
  esp.terraform.tfe_organization:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo    
    state: absent
    validate_certs: no
'''

RETURN = r'''
state:
    description: Organization state
    returned: always
    type: str
    sample: present
json:
    description: Details on organization.
    returned: success
    type: dict
    contains:
        data:
            description: Details on organization.
            returned: success
            type: dict                  
            sample:
                attributes:
                    collaborator-auth-policy: password
                    cost-estimation-enabled: true
                    created-at: 2021-04-23T20:55:40.419Z
                    email: jsmith@example.com
                    external-id: org-xvbiL33XypaReLcG
                    fair-run-queuing-enabled: false
                    name: foo
                    owners-team-saml-role-id: null
                    permissions:
                        can-access-via-teams: true
                        can-create-module: true
                        can-create-team: true
                        can-create-workspace: true
                        can-destroy: true
                        can-manage-sso: false
                        can-manage-subscription: true
                        can-manage-users: true
                        can-start-trial: false
                        can-traverse: true
                        can-update: true
                        can-update-agent-pools: false
                        can-update-api-token: true
                        can-update-oauth: true
                        can-update-sentinel: true
                        can-update-ssh-keys: true
                    plan-expired: false
                    plan-expires-at: null
                    plan-is-enterprise: false
                    plan-is-trial: false
                    saml-enabled: true
                    session-remember: 20160
                    session-timeout: 20160
                    two-factor-conformant: false
                id: foo
                links:
                    self: /api/v2/organizations/foo                
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_bytes, to_native, to_text

from ansible_collections.esp.terraform.plugins.module_utils.tfe_helper import TFEHelper


def main():
    argument_spec = TFEHelper.tfe_argument_spec()
    argument_spec.update(
        organization=dict(type='str', required=False, no_log=False),      
        state=dict(type='str', choices=['present', 'absent'], default='present'),
        attributes=dict(
            type='dict', 
            required=False, no_log=False,
        )
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,  
        required_one_of=[('organization', 'attributes')],
        mutually_exclusive=[('organization', 'attributes')],
        required_if=[('state', 'absent', ('organization',), True), ('state', 'present', ('attributes',), True)],        
    )

    tfe = TFEHelper(module)

    organization = module.params['organization']
    state = module.params['state']
    attributes = module.params['attributes']

    # Seed the result dict in the object
    result = dict(
        changed=False,
        state=state,
        json={},
    )
    if organization is not None:
        result['organization'] = organization
    if attributes is not None:
        result['attributes'] = attributes

    # Destroy the Organization if it exists and state == 'absent'
    if state == 'absent':

        existing_org_name = tfe.get_org_name_when_exists(organization=organization)

        if existing_org_name is not None:
            if not module.check_mode:            
                result['json'] = tfe.call_endpoint(tfe.api.orgs.destroy, org_name=existing_org_name)
            result['changed'] = True
 
    # Create or update the Organization if state == 'present'
    else:

        if organization is not None:
            attributes['name'] = organization

        if 'name' not in attributes:
            module.fail_json(msg='`name` is required when the `state` is `present`')

        o_payload = {
          "data": {
            "type": "organizations",
            "attributes": attributes
          }
        }

        existing_org_name = tfe.get_org_name_when_exists(organization=attributes['name'])

        # Create the Organization if it does not exist
        if existing_org_name is None:
            if not module.check_mode:  
                try:        
                    result['json'] = tfe.call_endpoint(tfe.api.orgs.create, payload=o_payload)
                except Exception as e:
                    module.fail_json(msg='Unable to create organization. Error: %s.' % (to_native(e)) )

            result['changed'] = True

        # Update the Organization if it exists
        else:

            try:        
                all_organizations = tfe.call_endpoint(tfe.api.orgs.list)
            except Exception as e:
                module.fail_json(msg='Unable to list organizations. Error: %s.' % (to_native(e)) )

            # Check if 'attributes' is a subset of current attributes, i.e. if there is any change
            current_attributes = [o for o in all_organizations['data'] if o['id'] == existing_org_name][0]['attributes']            
            if not tfe.is_subset(subset=attributes, superset=current_attributes):

                if not module.check_mode:  
                    try:        
                        result['json'] = tfe.call_endpoint(tfe.api.orgs.update, org_name=existing_org_name, payload=o_payload)
                    except Exception as e:
                        module.fail_json(msg='Unable to update "%s" organization. Error: %s.' % (existing_org_name, to_native(e)) )

                result['changed'] = True

    module.exit_json(**result)


if __name__ == '__main__':
    main()