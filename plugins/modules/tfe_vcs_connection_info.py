#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Krzysztof Lewandowski <krzysztof.lewandowski@nordea.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: tfe_vcs_connection_info
short_description: List VCS connections in the organization
description:
- Lists VCS connections between an organization and a VCS provider for use when creating or setting up workspaces.
- Information is retrieved from OAuth Clients defined from the organization.
- An OAuth Client represents the connection between an organization and a VCS provider.
- Details on an OAuth Client can be retrieved either by its ID or by its name.
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
  client:
    description:
    - List of OAuth clients (VCS connections) to retrieve details for.
    - This can be '*' which means all OAuth clients (VCS connections).
    - One may refer to an OAuth client either by its ID or its name.
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
- name: Retrieve details on all VCS connections in the organization
  esp.terraform.tfe_vcs_connection_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    client:
      - '*'
    validate_certs: no
  register: _result

- name: Retrieve details on the given VCS connections (supplied by names or IDs), in the organization
  esp.terraform.tfe_vcs_connection_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    client:
      - My Bitbucket
      - oc-4BWCffCgwSGYCrkW
    validate_certs: no
  register: _result
'''

RETURN = r'''
organization:
    description: Organization name or external-id.
    returned: always
    type: str
    sample: foo
oauth_clients:
    description: List of OAuth Clients (VCS connections) to retrieve details for.
    returned: always
    type: list
    elements: str
    sample:
        - My Bitbucket
        - oc-4BWCffCgwSGYCrkW
json:
    description: Details on OAuth Clients.
    returned: success
    type: dict
    contains:
        data:
            description: Details on OAuth Clients.
            returned: success
            type: list
            elements: dict                    
            sample:
                - attributes:
                      api-url: https://bitbucket.example.com
                      callback-url: "https://terraform.example.com/auth/2b81cf18-0e5a-48dc-95aa-cee4a15472b8/callback"
                      connect-path: "/auth/2b81cf18-0e5a-48dc-95aa-cee4a15472b8?organization_id=1"
                      http-url: https://bitbucket.example.com
                      key: 8eebbb1bf0a0f3a3e679fd0fb31b2647
                      name: My New Bitbucket
                      rsa-public-key: "-----BEGIN PUBLIC KEY- .... "
                      service-provider: bitbucket_server
                      service-provider-display-name: Bitbucket Server
                      tfvcs: false
                  id: oc-4BWCffCgwSGYCrkW
                  relationships:
                      oauth-tokens:
                          data:
                              - id: ot-o3MySY3Xo4nqbXBv
                                type: oauth-tokens
                          links:
                              related: /api/v2/oauth-clients/oc-4BWCffCgwSGYCrkW/oauth-tokens
                      organization:
                          data:
                              id: foo
                              type: organizations
                          links:
                              related: /api/v2/organizations/foo
                  type: oauth-clients                 
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_bytes, to_native, to_text

from ansible_collections.esp.terraform.plugins.module_utils.tfe_helper import TFEHelper


def main():
    argument_spec = TFEHelper.tfe_argument_spec()
    argument_spec.update(
        organization=dict(type='str', required=True, no_log=False),
        client=dict(type='list', elements='str', no_log=False, default=[ '*' ]),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,    
    )

    tfe = TFEHelper(module)
    
    organization = tfe.get_org_name_when_exists(organization=module.params['organization'])

    # Parse `client` parameter and create list of OAuth clients.
    # It's possible someone passed a comma separated string, so we should handle that.
    # This can be either an empty list or '*' which means all OAuth clients.
    clients = []
    clients = [p.strip() for p in module.params['client']]
    clients = tfe.listify_comma_sep_strings_in_list(clients)
    if not clients:
        clients = [ '*' ]

    # Seed the result dict in the object
    result = dict(
        changed=False,
        organization=organization,
        oauth_clients=clients,
        json={},
    )

    # Set organization
    try:        
        tfe.call_endpoint(tfe.api.set_org, org_name=organization)
    except Exception as e:
        module.fail_json(msg='Unable to set "%s" organization to use for org specific endpoints: %s' % (organization, to_native(e)))
    
    if '*' in clients:
        # Retrieve information for all OAuth clients
        try:        
            result['json'] = tfe.call_endpoint(tfe.api.oauth_clients.list)
        except Exception as e:
            module.fail_json(msg='Unable to list OAuth Clients in "%s" organization. Error: %s.' % (organization, to_native(e)) )
    else:
        result['json']['data'] = []
        # First, get the list of all OAuth clients
        try:        
            all_oauth_clients = tfe.call_endpoint(tfe.api.oauth_clients.list)
        except Exception as e:
            module.fail_json(msg='Unable to list OAuth Clients in "%s" organization. Error: %s.' % (organization, to_native(e)) )

        # Next, iterate over the supplied OAuth clients to retrieve their details
        for client in clients:

            # Refer to an OAuth client by its name
            if any(oc['attributes']['name'] == client for oc in all_oauth_clients['data']):
                try:
                    client_id = [oc for oc in all_oauth_clients['data'] if oc['attributes']['name'] == client][0]['id']
                    ret = tfe.call_endpoint(tfe.api.oauth_clients.show, client_id=client_id)
                except Exception as e:
                    #module.fail_json(msg='Unable to retrieve details on an OAuth Client in "%s" organization. Error: %s.' % (organization, to_native(e)) )
                    ret = None

            # Refer to an OAuth client by its ID
            else:
                try:        
                    ret = tfe.call_endpoint(tfe.api.oauth_clients.show, client_id=client)
                except Exception as e:
                    #module.fail_json(msg='Unable to retrieve details on an OAuth Client in "%s" organization. Error: %s.' % (organization, to_native(e)) )
                    ret = None

            if ret is not None:
                result['json']['data'].append(ret['data'])           

    module.exit_json(**result)


if __name__ == '__main__':
    main()