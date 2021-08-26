#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Krzysztof Lewandowski <krzysztof.lewandowski@nordea.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: tfe_user_token_info
short_description: List user tokens
description:
- Lists user tokens.
- The objects returned by this module only contain metadata, and do not include the secret text of any authentication tokens. 
- A token is only shown upon creation, and cannot be recovered later.
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
  user:
    description:
    - Terraform user.
    - One may refer to a user either by its id, email or its name.  
    type: str
    required: true  
  user_token:
    description:
    - List of user tokens to retrieve details for.
    - This can be '*' which means all user tokens.
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
- name: Retrieve details on all user tokens, user supplied by email
  esp.terraform.tfe_user_token_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    user: jsmith@example.com
    user_token:
      - '*'
    validate_certs: no
  register: _result

- name: Retrieve details on all user tokens, user supplied by id
  esp.terraform.tfe_user_token_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    user: user-ctVahEhZNb22D5Se
    user_token:
      - '*'
    validate_certs: no
  register: _result

- name: Retrieve details on the given user tokens, user supplied by login
  esp.terraform.tfe_user_token_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    user: ann_doe
    user_token:
      - at-QmATJea6aWj1xR2t
    validate_certs: no
  register: _result
'''

RETURN = r'''
json:
    description: Details on user tokens.
    returned: success
    type: dict
    contains:
        data:
            description: Details on user tokens.
            returned: success
            type: list
            elements: dict                    
            sample:
                - attributes:
                      created-at: 2021-04-20T11:21:10.755Z
                      description: user token
                      last-used-at: 2021-04-25T22:36:14.038Z
                      token: null
                  id: at-zkxJyuwX6MMhQWEw
                  relationships:
                      created-by:
                          data:
                              id: user-K1LWGyjmnDL59y4H
                              type: users
                  type: authentication-tokens              
'''

import collections

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_bytes, to_native, to_text

from ansible_collections.esp.terraform.plugins.module_utils.tfe_helper import TFEHelper


def main():
    argument_spec = TFEHelper.tfe_argument_spec()
    argument_spec.update(
        user=dict(type='str', required=True, no_log=False),
        user_token=dict(type='list', elements='str', no_log=False, default=[ '*' ]),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,    
    )

    tfe = TFEHelper(module)

    user = module.params['user']

    # Parse `user_token` parameter and create list of user tokens.
    # It's possible someone passed a comma separated string, so we should handle that.
    # This can be either an empty list or '*' which means all user tokens.
    tokens = module.params['user_token']
    if isinstance(module.params['user_token'], collections.Iterable):
        tokens = [p.strip() for p in module.params['user_token']]
        tokens = tfe.listify_comma_sep_strings_in_list(tokens)
    if not tokens:
        tokens = [ '*' ]

    # Seed the result dict in the object
    result = dict(
        changed=False,
        user=user,
        user_tokens=tokens,
        json={},
    )

    # Set organization
    orgs = tfe.call_endpoint(tfe.api.orgs.list)
    try:        
        tfe.call_endpoint(tfe.api.set_org, org_name=orgs['data'][0]['id'])
    except Exception as e:
        module.fail_json(msg='Unable to set "%s" organization to use for org specific endpoints: %s' % (organization, to_native(e)))

    # Retrieve information about all users
    try:        
        all_users = tfe.call_endpoint(tfe.api.admin_users._list_all, url=tfe.TFE_URL + "/api/v2/admin/users", include=None)
    except Exception as e:
        module.fail_json(msg='Unable to list users. Error: %s.' % (to_native(e)) )

    if any(u['id'] == user or u['attributes']['email'] == user or u['attributes']['username'] == user for u in all_users['data']):
        u = [u for u in all_users['data'] if u['id'] == user or u['attributes']['email'] == user or u['attributes']['username'] == user][0]
    else:
        module.fail_json(msg='Unable to retrieve details on "%s" user. It does not exist.' % (user) )

    # If list of Token IDs is provided, then simply get their details
    if '*' not in tokens:
        result['json']['data'] = []

        # Iterate over the supplied OAuth tokens to retrieve their details
        for token in tokens:

            try:        
                ret = tfe.call_endpoint(tfe.api.user_tokens.show, token_id=token)
            except Exception as e:
                module.fail_json(msg='Unable to retrieve details on "%s" user token. Error: %s.' % (token, to_native(e)) )

            result['json']['data'].append(ret['data'])  

    # If '*' is provided in the list of tokens, then get all tokens for the given user
    else:

        # Get the list of all user tokens
        try:        
            result['json'] = tfe.call_endpoint(tfe.api.user_tokens.list, user_id=u['id'])
        except Exception as e:
            module.fail_json(msg='Unable to list user tokens for "%s" user. Error: %s.' % (user, to_native(e)) )

    module.exit_json(**result)


if __name__ == '__main__':
    main()