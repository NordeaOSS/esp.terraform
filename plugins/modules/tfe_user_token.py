#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Krzysztof Lewandowski <krzysztof.lewandowski@nordea.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: tfe_user_token
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
    - Definition of the attributes for user token.
    - Required when C(state=present).       
    type: dict
    suboptions:
      description:
        description:
        - The description for the User Token
        type: str
        required: false    
  user_token:
    description:
    - User token ID to remove.   
    - Required when C(state=absent).      
    type: str
    required: false
  state:
    description:
    - Whether the user token should exist or not.
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
- name: Create a User Token
  esp.terraform.tfe_user_token:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    attributes:
      description: API
    state: present
    validate_certs: no
  register: _result

- name: Display the token
  debug:
    msg: "{{ _result.json.data.attributes.token }}"

- name: Destroy a User Token
  esp.terraform.tfe_user_token:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    user_token: at-QmATJea6aWj1xR2t
    state: absent
    validate_certs: no    
'''

RETURN = r'''
json:
    description: Details on user token.
    returned: success
    type: dict
    contains:
        data:
            description: Details on user token.
            returned: success
            type: dict                
            sample:
                attributes:
                    created-at: 2021-04-26T07:53:37.328Z
                    description: API
                    last-used-at: null
                    token: bayN9KGosVRBlw.atlasv1.rVh8hWQ7kiiFNP6FVeAhWocHVKQhPiUcsQ7yDLYMuYijUPIjxGmybbYCnUX88oguXYA
                id: at-mvnJnf6cpbcjRbvd
                relationships:
                    created-by:
                        data:
                            id: user-K1LWGyjmnDL59y4H
                            type: users
                type: authentication-tokens                 
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_bytes, to_native, to_text

from ansible_collections.esp.terraform.plugins.module_utils.tfe_helper import TFEHelper


def main():
    argument_spec = TFEHelper.tfe_argument_spec()
    argument_spec.update(
        state=dict(type='str', choices=['present', 'absent'], default='present'),
        user_token=dict(type='str', required=False, no_log=False),
        attributes=dict(
            type='dict', 
            required=False, no_log=False,
        )
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,  
        required_if=[('state', 'present', ('attributes',), True), ('state', 'absent', ('user_token',), True)],
    )

    tfe = TFEHelper(module)
    
    state = module.params['state']
    user_token = module.params['user_token']
    attributes = module.params['attributes']

    # Seed the result dict in the object
    result = dict(
        changed=False,
        state=state,
        json={},
    )
    if user_token is not None:
        result['user_token'] = user_token
    if attributes is not None:
        result['attributes'] = attributes

    # Set organization
    orgs = tfe.call_endpoint(tfe.api.orgs.list)
    try:        
        tfe.call_endpoint(tfe.api.set_org, org_name=orgs['data'][0]['id'])
    except Exception as e:
        module.fail_json(msg='Unable to set "%s" organization to use for org specific endpoints: %s' % (organization, to_native(e)))

    # Get your account details
    try:        
        account_details = tfe.call_endpoint(tfe.api.account.show)
    except Exception as e:
        module.fail_json(msg='Unable to get the current user account details: %s' % (to_native(e)))
    
    # Remove the user token if it exists and state == 'absent'
    if state == 'absent':
    
        # Get the list of all user tokens
        try:        
            all_tokens = tfe.call_endpoint(tfe.api.user_tokens.list, user_id=account_details['data']['id'])
        except Exception as e:
            module.fail_json(msg='Unable to list user tokens for "%s" user. Error: %s.' % (account_details['data']['attributes']['email'], to_native(e)) )

        # Check if the supplied token exists
        matching_token = [at for at in all_tokens['data'] if at['id'] == user_token]
        if len(matching_token) == 1:

            if not module.check_mode: 
                try:        
                    result['json'] = tfe.call_endpoint(tfe.api.user_tokens.destroy, token_id=user_token)
                except Exception as e:
                    module.fail_json(msg='Unable to destroy "%s" User Token. Error: %s.' % (user_token, to_native(e)) )
                  
            result['changed'] = True

        else:
            module.fail_json(msg='Unable to find "%s" token. It does not exist.' % (user_token) ) 

    # Create the user token if state == 'present'
    if state == 'present':

        create_ut_payload = {
          "data": {
            "type": "authentication-tokens",
            "attributes": attributes
          }
        }

        if not module.check_mode: 
            try:        
                result['json'] = tfe.call_endpoint(tfe.api.user_tokens.create, user_id=account_details['data']['id'], payload=create_ut_payload)
            except Exception as e:
                module.fail_json(msg='Unable to create user token. Error: %s.' % (to_native(e)) )

        result['changed'] = True

    module.exit_json(**result)


if __name__ == '__main__':
    main()