#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Krzysztof Lewandowski <krzysztof.lewandowski@nordea.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: tfe_vcs_token
short_description: Manage VCS tokens
description:
- Updates or removes a VCS tokens.
- The OAuth Token object represents a VCS configuration which includes the OAuth connection and the associated OAuth token.
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
  attributes:
    description:
    - Definition of the attributes for VCS token.
    - Required when C(state=present).       
    type: dict
    suboptions:
      ssh-key:
        description:
        - Private SSH key to associate with VCS token.
        type: str
        required: false    
  oauth_token:
    description:
    - OAuth token (VCS token) ID to update or remove.   
    type: str
    required: false
  state:
    description:
    - Whether the OAuth client (VCS connection) should exist or not.
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
- name: Update a VCS token, add or replace ssh private key
  esp.terraform.tfe_vcs_token:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    oauth_token: ot-DxHXyuZUBxZN9g9G
    attributes:
      "ssh-key": "{{ lookup('file', '~/ssh/private.key') }}"
    state: present
    validate_certs: no

- name: Remove a VCS token
  esp.terraform.tfe_vcs_token:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo    
    oauth_token: ot-DxHXyuZUBxZN9g9G
    state: absent
    validate_certs: no    
'''

RETURN = r'''
organization:
    description: Organization name or external-id.
    returned: always
    type: str
    sample: foo
state:
    description: OAuth Token state
    returned: always
    type: str
    sample: present
json:
    description: Details on OAuth Token.
    returned: success
    type: dict
    contains:
        data:
            description: Details on OAuth Clients.
            returned: success
            type: dict                
            sample:
                attributes:
                    created-at: "2021-04-22T19:51:24.395Z"
                    has-ssh-key: true
                    service-provider-user: null
                id: ot-DxHXyuZUBxZN9g9G
                relationships:
                    oauth-client:
                        data:
                            id: oc-dQnkeDhvm9ytHxwM
                            type: oauth-clients
                        links:
                            related: /api/v2/oauth-clients/oc-dQnkeDhvm9ytHxwM
                type: oauth-tokens                 
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_bytes, to_native, to_text

from ansible_collections.esp.terraform.plugins.module_utils.tfe_helper import TFEHelper


def main():
    argument_spec = TFEHelper.tfe_argument_spec()
    argument_spec.update(
        organization=dict(type='str', required=True, no_log=False),
        state=dict(type='str', choices=['present', 'absent'], default='present'),
        oauth_token=dict(type='str', required=True, no_log=False),
        attributes=dict(
            type='dict', 
            required=False, no_log=True,
        )
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,  
        required_if=[('state', 'present', ('attributes',), True)],
    )

    tfe = TFEHelper(module)
    
    organization = tfe.get_org_name_when_exists(organization=module.params['organization'])
    state = module.params['state']
    oauth_token = module.params['oauth_token']
    attributes = module.params['attributes']

    # Seed the result dict in the object
    result = dict(
        changed=False,
        organization=organization,
        oauth_token=oauth_token,
        state=state,
        json={},
    )

    # Set organization
    try:        
        tfe.call_endpoint(tfe.api.set_org, org_name=organization)
    except Exception as e:
        module.fail_json(msg='Unable to set "%s" organization to use for org specific endpoints: %s' % (organization, to_native(e)))
    
    # Get the list of all OAuth clients
    try:        
        all_oauth_clients = (tfe.call_endpoint(tfe.api.oauth_clients.list))['data']
    except Exception as e:
        module.fail_json(msg='Unable to list OAuth Clients in "%s" organization. Error: %s.' % (organization, to_native(e)) )
    
    # Get the list of all OAuth tokens
    all_oauth_tokens = []
    for client in all_oauth_clients:
        try:        
            all_oauth_tokens.extend( (tfe.call_endpoint(tfe.api.oauth_tokens.list, oauth_client_id=client['id']))['data'] )
        except Exception as e:
            module.fail_json(msg='Unable to list OAuth Tokens for "%s" OAuth client. Error: %s.' % (client, to_native(e)) )

    # Check if the supplied token exists
    matching_token = [ot for ot in all_oauth_tokens if ot['id'] == oauth_token]

    # Remove the OAuth token if it exists and state == 'absent'
    if (state == 'absent') and (len(matching_token) == 1):
    
        if not module.check_mode: 
            try:        
                result['json'] = tfe.call_endpoint(tfe.api.oauth_tokens.destroy, token_id=oauth_token)
            except Exception as e:
                module.fail_json(msg='Unable to destroy "%s" OAuth Token. Error: %s.' % (oauth_token, to_native(e)) )
           
        result['changed'] = True
 
    # Update the OAuth token if it exists state == 'present'
    if (state == 'present') and (len(matching_token) == 1):

        update_ot_payload = {
          "data": {
            "id": oauth_token,
            "type": "oauth-tokens",
            "attributes": attributes
          }
        }  

        if not module.check_mode: 
            try:        
                result['json'] = tfe.call_endpoint(tfe.api.oauth_tokens.update, token_id=oauth_token, payload=update_ot_payload)
            except Exception as e:
                module.fail_json(msg='Unable to update "%s" OAuth Token. Error: %s.' % (oauth_token, to_native(e)) )

        result['changed'] = True

    module.exit_json(**result)


if __name__ == '__main__':
    main()