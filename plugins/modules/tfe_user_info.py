#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Krzysztof Lewandowski <krzysztof.lewandowski@nordea.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: tfe_user_info
short_description: List user accounts
description:
- Lists user accounts in the Terraform Enterprise installation.
- Details on a given user can be retrieved either by its id, email or by its name.
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
    - List of users to retrieve details for.
    - This can be '*' which means all users.
    - One may refer to a user either by its id, email or its name.    
    type: list
    required: true
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
- name: Retrieve details on all users
  esp.terraform.tfe_user_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    user:
      - '*'
    validate_certs: no
  register: _result

- name: Retrieve details on given users (supplied by names, emails or IDs)
  esp.terraform.tfe_user_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    user:
      - jsmith@example.com
      - ann_doe
      - user-ctVahEhZNb22D5Se
    validate_certs: no
  register: _result
'''

RETURN = r'''
json:
    description: Details on users.
    returned: success
    type: dict
    contains:
        data:
            description: Details on users.
            returned: success
            type: list
            elements: dict            
            sample:
                - attributes:
                      avatar-url: https://www.gravatar.com/avatar/73e8b34b8de0f050f5fdd7960ef0c756?s=100&d=mm
                      email: jsmith@example.com
                      is-admin: true
                      is-service-account: false
                      is-suspended: false
                      two-factor:
                          enabled: false
                          verified: false
                      username: john_smith
                  id: user-K1LWGyjmnDL59y4H
                  links:
                      self: /api/v2/users/user-K1LWGyjmnDL59y4H
                  relationships:
                      authentication-tokens:
                          links:
                              related: /api/v2/users/user-K1LWGyjmnDL59y4H/authentication-tokens
                      organizations:
                          data:
                                - id: foo
                                  type: organizations
                  type: users
'''

import collections

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_bytes, to_native, to_text

from ansible_collections.esp.terraform.plugins.module_utils.tfe_helper import TFEHelper


def main():
    argument_spec = TFEHelper.tfe_argument_spec()
    argument_spec.update(
        user=dict(type='list', elements='str', no_log=False, default=[ '*' ]),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,    
    )

    tfe = TFEHelper(module)

    # Parse `user` parameter and create list of users.
    # It's possible someone passed a comma separated string, so we should handle that.
    # This can be either an empty list or '*' which means all users.
    users = module.params['user']
    if isinstance(module.params['user'], collections.Iterable):
        users = [p.strip() for p in module.params['user']]
        users = tfe.listify_comma_sep_strings_in_list(users)
    if not users:
        users = [ '*' ]

    # Seed the result dict in the object
    result = dict(
        changed=False,
        users=users,
        json={},
    )

    # Retrieve information about all users
    try:        
        all_users = tfe.call_endpoint(tfe.api.admin_users._list_all, url=tfe.TFE_URL + "/api/v2/admin/users", include=None)
    except Exception as e:
        module.fail_json(msg='Unable to list users. Error: %s.' % (to_native(e)) )

    if '*' in users:
        result['json'] = all_users

    else:
        result['json']['data'] = []
        # Iterate over the supplied users to retrieve their details
        for user in users:

            if any(u['id'] == user or u['attributes']['email'] == user or u['attributes']['username'] == user for u in all_users['data']):
                u = [u for u in all_users['data'] if u['id'] == user or u['attributes']['email'] == user or u['attributes']['username'] == user][0]
            else:
                module.fail_json(msg='Unable to retrieve details on "%s" user. It does not exist.' % (user) )

            # try:        
            #     ret = tfe.call_endpoint(tfe.api.users.show, user_id=user_id)
            # except Exception as e:
            #     module.fail_json(msg='Unable to retrieve details on "%s" user. Error: %s.' % (user, to_native(e)) )

            result['json']['data'].append(u)
           
    module.exit_json(**result)


if __name__ == '__main__':
    main()