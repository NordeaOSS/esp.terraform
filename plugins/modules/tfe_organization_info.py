#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Krzysztof Lewandowski <krzysztof.lewandowski@nordea.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: tfe_organization_info
short_description: List Terraform Enterprise organizations
description:
- Lists Terraform Enterprise organizations.
- Details on an organization can be retrieved either by its external-id or by its name.
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
    - List of organizations to retrieve details for.
    - This can be '*' which means all organizations.
    - One may refer to a workspace either by its external-id or its name.    
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
- name: Retrieve details on all organizations
  esp.terraform.tfe_organization_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization:
      - '*'
    validate_certs: no
  register: _result

- name: Retrieve details on given organizations (supplied by names or IDs)
  esp.terraform.tfe_organization_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization:
      - foo
      - org-ujAdbddGRe7dn6NU
    validate_certs: no
  register: _result
'''

RETURN = r'''
organization:
    description: List of organizations to retrieve details for.
    returned: always
    type: list
    elements: dict
    sample:
        - foo
json:
    description: Details on organizations.
    returned: success
    type: dict
    contains:
        data:
            description: Details on organizations.
            returned: success
            type: list
            elements: dict            
            sample:
                - attributes:
                      collaborator-auth-policy: password
                      cost-estimation-enabled: true
                      created-at: 2021-04-21T13:14:31.465Z
                      email: admin@example.com
                      external-id: org-ujAdbddGRe7dn6NU
                      fair-run-queuing-enabled: false
                      global-module-sharing: false
                      module-consuming-organizations-count: 0
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
                      session-remember: null
                      session-timeout: null
                      two-factor-conformant: false
                  id: foo
                  links:
                      self: /api/v2/organizations/foo
                  relationships:
                      authentication-token:
                          links:
                              related: /api/v2/organizations/foo/authentication-token
                      entitlement-set:
                          data:
                              id: org-ujAdbddGRe7dn6NU
                              type: entitlement-sets
                          links:
                              related: /api/v2/organizations/foo/entitlement-set
                      module-producers:
                          links:
                              related: /api/v2/organizations/foo/relationships/module-producers
                      oauth-tokens:
                          links:
                              related: /api/v2/organizations/foo/oauth-tokens
                      subscription:
                          links:
                              related: /api/v2/organizations/foo/subscription
                  type: organizations
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_bytes, to_native, to_text

from ansible_collections.esp.terraform.plugins.module_utils.tfe_helper import TFEHelper


def main():
    argument_spec = TFEHelper.tfe_argument_spec()
    argument_spec.update(
        organization=dict(type='list', elements='str', no_log=False, default=[ '*' ]),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,    
    )

    tfe = TFEHelper(module)

    # Parse `organization` parameter and create list of organizations.
    # It's possible someone passed a comma separated string, so we should handle that.
    # This can be either an empty list or '*' which means all organizations.
    organizations = []
    organizations = [p.strip() for p in module.params['organization']]
    organizations = tfe.listify_comma_sep_strings_in_list(organizations)
    if not organizations:
        organizations = [ '*' ]

    # Seed the result dict in the object
    result = dict(
        changed=False,
        organizations=organizations,
        json={},
    )

    result['json']['data'] = []
    result['json']['not_found'] = []

    # Retrieve information for all organizations
    try:        
        all_organizations = tfe.call_endpoint(tfe.api.orgs.list)
    except Exception as e:
        module.fail_json(msg='Unable to list organizations. Error: %s.' % (to_native(e)) )

    if '*' in organizations:

        for org in all_organizations['data']:

            try:        
                entitlements = tfe.call_endpoint(tfe.api.orgs.entitlements, org_name=org['id'])
            except Exception as e:
                module.fail_json(msg='Unable to retrieve details on "%s" organization. Error: %s.' % (org['id'], to_native(e)) )

            try:        
                module_producers = tfe.call_endpoint(tfe.api.orgs.show_module_producers, org_name=org['id'])
            except Exception as e:
                module.fail_json(msg='Unable to retrieve details on "%s" organization. Error: %s.' % (org['id'], to_native(e)) )
        
            org['entitlements'] = entitlements['data']
            org['module_producers'] = module_producers['data']
            result['json']['data'].append(org)

    else:
        # Iterate over the supplied organizations to retrieve their details
        for organization in organizations:

            # Refer to an organization by its external-id
            if any(o['attributes']['external-id'] == organization for o in all_organizations['data']):
                org_name = [o for o in all_organizations['data'] if o['attributes']['external-id'] == organization][0]['id'] 
            # Refer to an organization by its name
            else:
                org_name = organization

            try:        
                ret = tfe.call_endpoint(tfe.api.orgs.show, org_name=org_name)
            except Exception as e:
                #module.fail_json(msg='Unable to retrieve details on "%s" organization. Error: %s.' % (organization, to_native(e)) )
                result['json']['not_found'].append( organization )
                ret = None

            if ret is not None:
                try:        
                    entitlements = tfe.call_endpoint(tfe.api.orgs.entitlements, org_name=org_name)
                except Exception as e:
                    module.fail_json(msg='Unable to retrieve details on "%s" organization. Error: %s.' % (organization, to_native(e)) )

                try:        
                    module_producers = tfe.call_endpoint(tfe.api.orgs.show_module_producers, org_name=org_name)
                except Exception as e:
                    module.fail_json(msg='Unable to retrieve details on "%s" organization. Error: %s.' % (organization, to_native(e)) )
            
                ret['data']['entitlements'] = entitlements['data']
                ret['data']['module_producers'] = module_producers['data']

                result['json']['data'].append(ret['data'])            
           
    module.exit_json(**result)


if __name__ == '__main__':
    main()