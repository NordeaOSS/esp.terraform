#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Krzysztof Lewandowski <krzysztof.lewandowski@nordea.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: tfe_organization_membership_info
short_description: List organization memberships
description:
- Lists organization memberships.
- Organization memberships are searchable by user name, email or membership ID.
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
    - The name of the organization to list the memberships of.
    type: str
    required: true
  membership:
    description:
    - List of organization memberships to retrieve details for.
    - Organization memberships are searchable by user name, email, user ID or membership ID.
    - The list can contain elements in any of these formats.
    - This can be '*' which means all memberships in the organization.
    type: list
    required: false
    default: [ '*' ]
  status:
    description:
    - If specified, restricts results to those with the matching status value. Valid values are C(invited) and C(active).
    type: str
    choices: [ invited, active ]
    required: false
  include:
    description:
    - Return additional information about nested resources.
    - This can be any of C(user) and C(teams).
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
- name: Retrieve details on all active organization memberships, include additional information about user and teams
  esp.terraform.tfe_organization_membership_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    membership:
      - '*'
    status: active
    include:
      - user
      - teams
    validate_certs: no
  register: _result

- name: Retrieve details on the supplied organization memberships, restricts results to active memberships
  esp.terraform.tfe_organization_membership_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    membership:
      - jsmith@example.com
      - ou-SKVvnWhoTxWrofkE
      - user-K1LWGyjmnDL59y4H
      - john_doe
    status: active
    validate_certs: no
  register: _result

- name: Display all invited memberships in the supplied organization
  esp.terraform.tfe_organization_membership_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    membership:
      - '*'
    status: invited
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
    description: Details on memberships.
    returned: success
    type: dict
    contains:
        data:
            description: Details on memberships.
            returned: success
            type: list
            elements: dict            
            sample:
                - attributes:
                      created-at: 2021-04-21T13:14:31.483Z
                      email: jsmith@example.com
                      status: active
                  id: ou-SKVvnWhoTxWrofkE
                  relationships:
                      organization:
                          data:
                              id: foo
                              type: organizations
                      teams:
                          data:
                              - id: team-VQ1FncissQs9Bom8
                                type: teams
                      user:
                          data:
                              id: user-K1LWGyjmnDL59y4H
                              type: users
                  type: organization-memberships               
        included:
            description: Additional information about nested resources.
            returned: success
            type: list
            elements: dict 
'''

import collections

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_bytes, to_native, to_text

from ansible_collections.esp.terraform.plugins.module_utils.tfe_helper import TFEHelper


def main():
    argument_spec = TFEHelper.tfe_argument_spec()
    argument_spec.update(
        organization=dict(type='str', required=True, no_log=False),
        membership=dict(type='list', elements='str', no_log=False, default=[ '*' ]),
        status=dict(type='str', required=False, no_log=False, choices=['invited', 'active']),        
        include=dict(type='list', elements='str', no_log=False, required=False, choices=['user', 'teams']),        
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,    
    )

    tfe = TFEHelper(module)

    organization = tfe.get_org_name_when_exists(organization=module.params['organization'])
    status = module.params['status']
    include = module.params['include']

    # Parse `membership` parameter and create list of memberships.
    # It's possible someone passed a comma separated string, so we should handle that.
    # This can be either an empty list or '*' which means all memberships.
    memberships = module.params['membership']
    if isinstance(module.params['membership'], collections.Iterable):
        memberships = [p.strip() for p in module.params['membership']]
        memberships = tfe.listify_comma_sep_strings_in_list(memberships)
    if not memberships:
        memberships = [ '*' ]

    # Seed the result dict in the object
    result = dict(
        changed=False,
        organization=organization,
        memberships=memberships,
        json={},
    )
    if status is not None:
        result['status'] = status
        
    if include is not None:
        result['include'] = include

    # Seed the filters list
    filters = None
    if status is not None:
        filters = [
            {
                "keys": ["status"],
                "value": status
            }
        ]

    # Set organization
    try:        
        tfe.call_endpoint(tfe.api.set_org, org_name=organization)
    except Exception as e:
        module.fail_json(msg='Unable to set "%s" organization to use for org specific endpoints: %s' % (organization, to_native(e)))
    
    if '*' in memberships:
        # Retrieve information for all memberships
        try:        
            result['json'] = tfe.call_endpoint(tfe.api.org_memberships.list_all_for_org, query=None, filters=filters, include=include)
        except Exception as e:
            module.fail_json(msg='Unable to list memberships in "%s" organization. Error: %s.' % (organization, to_native(e)) )
    else:
        result['json']['data'] = []
        result['json']['included'] = []
        # First, get the list of all memberships
        try:        
            all_memberships = tfe.call_endpoint(tfe.api.org_memberships.list_all_for_org, query=None, filters=filters, include=["user"])
        except Exception as e:
            module.fail_json(msg='Unable to list memberships in "%s" organization. Error: %s.' % (organization, to_native(e)) )        

        # Next, iterate over the supplied memberships to retrieve their details
        for membership in memberships:

            # Refer to a memberships by user email
            if any(m['attributes']['email'] == membership for m in all_memberships['data']):
                matching_membership = [m for m in all_memberships['data'] if m['attributes']['email'] == membership][0]['attributes']['email']
                try:        
                    ret = tfe.call_endpoint(tfe.api.org_memberships.list_all_for_org, query=matching_membership, filters=filters, include=include)
                except Exception as e:
                    module.fail_json(msg='Unable to retrieve details on "%s" membership in "%s" organization. Error: %s.' % (membership, organization, to_native(e)) )

            # Refer to a memberships by membership ID
            elif any(m['id'] == membership for m in all_memberships['data']):
                try:        
                    ret = tfe.call_endpoint(tfe.api.org_memberships.show, org_membership_id=membership, include=include)
                except Exception as e:
                    module.fail_json(msg='Unable to retrieve details on "%s" membership in "%s" organization. Error: %s.' % (membership, organization, to_native(e)) )

            # Try to find a user by their name or ID
            else:
                matching_membership = None
                for m in all_memberships['data']:
                    user_id = m['relationships']['user']['data']['id']
                    if user_id == membership:
                        matching_membership = m['attributes']['email']
                        break
                    else:
                        if any(include['id'] == user_id and include['attributes']['username'] == membership for include in all_memberships['included']):
                            matching_membership = [include for include in all_memberships['included'] if include['id'] == user_id and include['attributes']['username'] == membership][0]['attributes']['username']
                            break

                if matching_membership is not None:
                    try:        
                        ret = tfe.call_endpoint(tfe.api.org_memberships.list_all_for_org, query=matching_membership, filters=filters, include=include)
                    except Exception as e:
                        module.fail_json(msg='Unable to retrieve details on "%s" membership in "%s" organization. Error: %s.' % (membership, organization, to_native(e)) )
                else:
                    module.fail_json(msg='Unable to retrieve details on "%s" membership in "%s" organization.' % (membership, organization) )

            result['json']['data'].extend(ret['data'])
            if include is not None:
                result['json']['included'].extend(ret['included'])            

    module.exit_json(**result)


if __name__ == '__main__':
    main()