#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Krzysztof Lewandowski <krzysztof.lewandowski@nordea.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: tfe_vcs_token_info
short_description: List VCS tokens for a given VCS connection
description:
- List the OAuth Tokens (VCS tokens) for a given OAuth Client (VCS connection).
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
  client:
    description:
    - OAuth client (VCS connection) to retrieve tokens for.
    - One may refer to an OAuth client (VCS connection) either by its ID or its name.
    - If not specified, all OAuth Tokens (VCS tokens) in the organization will be searched for.
    type: str
    required: false
  oauth_token:
    description:
    - List of OAuth Tokens (VCS tokens) to retrieve details for.
    - This can be '*' which means all OAuth Tokens (VCS tokens).
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
- name: Retrieve details on all VCS tokens in the organization
  esp.terraform.tfe_vcs_token_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    oauth_token:
      - '*'
    validate_certs: no
  register: _result

- name: Retrieve details on all VCS tokens for a given VCS connection (supplied by name)
  esp.terraform.tfe_vcs_token_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    client: My Bitbucket
    oauth_token:
      - '*'
    validate_certs: no
  register: _result

- name: Retrieve details on the given VCS tokens for a given VCS connection (supplied by ID)
  esp.terraform.tfe_vcs_token_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    client: oc-dQnkeDhvm9ytHxwM
    oauth_token:
      - ot-DxHXyuZUBxZN9g9G
    validate_certs: no
  register: _result
'''

RETURN = r'''
organization:
    description: Organization name or external-id.
    returned: always
    type: str
    sample: foo
oauth_client:
    description: OAuth Client (VCS connections).
    returned: always
    type: str
    sample: My Bitbucket   
oauth_tokens:
    description: List of OAuth Tokens (VCS tokens) to retrieve details for.
    returned: always
    type: list
    elements: str
    sample:
        - ot-DxHXyuZUBxZN9g9G
json:
    description: Details on OAuth Tokens.
    returned: success
    type: dict
    contains:
        data:
            description: Details on OAuth Tokens.
            returned: success
            type: list
            elements: dict                    
            sample:
                - attributes:
                      created-at: "2021-04-22T19:51:24.395Z"
                      has-ssh-key: false
                      service-provider-user: null
                  id: ot-DxHXyuZUBxZN9g9G
                  links:
                      self: /api/v2/oauth-tokens/ot-DxHXyuZUBxZN9g9G
                  relationships:
                      oauth-client:
                          data:
                              - id: oc-dQnkeDhvm9ytHxwM
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
        client=dict(type='str', required=False, no_log=False),
        oauth_token=dict(type='list', elements='str', no_log=False, default=[ '*' ]),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,    
    )

    tfe = TFEHelper(module)

    organization = tfe.get_org_name_when_exists(organization=module.params['organization'])
    client = module.params['client']

    # Parse `oauth_token` parameter and create list of OAuth tokens.
    # It's possible someone passed a comma separated string, so we should handle that.
    # This can be either an empty list or '*' which means all OAuth tokens.
    tokens = []
    tokens = [p.strip() for p in module.params['oauth_token']]
    tokens = tfe.listify_comma_sep_strings_in_list(tokens)
    if not tokens:
        tokens = [ '*' ]

    # Seed the result dict in the object
    result = dict(
        changed=False,
        organization=organization,
        oauth_client=client,
        oauth_tokens=tokens,
        json={},
    )

    # Set organization
    try:        
        tfe.call_endpoint(tfe.api.set_org, org_name=organization)
    except Exception as e:
        module.fail_json(msg='Unable to set "%s" organization to use for org specific endpoints: %s' % (organization, to_native(e)))
    
    result['json']['data'] = []

    # If list of Token IDs is provided, then simply get their details
    if '*' not in tokens:
        # Iterate over the supplied OAuth tokens to retrieve their details
        for token in tokens:

            try:        
                ret = tfe.call_endpoint(tfe.api.oauth_tokens.show, token_id=token)
            except Exception as e:
                module.fail_json(msg='Unable to retrieve details on "%s" OAuth Token. Error: %s.' % (token, to_native(e)) )

            result['json']['data'].append(ret['data'])  

    # If '*' is provided in the list of tokens, then grab them either for the supplied client, or for all clients
    else:

        # Get the list of all OAuth clients
        try:        
            all_oauth_clients = tfe.call_endpoint(tfe.api.oauth_clients.list)
        except Exception as e:
            module.fail_json(msg='Unable to list OAuth Clients in "%s" organization. Error: %s.' % (organization, to_native(e)) )

        # If VCS connection (OAuth client) is supplied
        if client is not None:
            # Find OAuth Client ID
            client_id = None
            matching_clients = [oc for oc in all_oauth_clients['data'] if oc['attributes']['name'] == client]
            if len(matching_clients) == 1:
                client_id = matching_clients[0]['id']
            if client_id is None:
                client_id = client

            if not any(oc['id'] == client_id for oc in all_oauth_clients['data']):
                module.fail_json(msg='Unable to find the supplied "%s OAuth client in "%s" organization.' % (client, organization) )

            # Retrieve information for all OAuth tokens
            try:        
                result['json'] = tfe.call_endpoint(tfe.api.oauth_tokens.list, oauth_client_id=client_id)
            except Exception as e:
                module.fail_json(msg='Unable to list OAuth Tokens for "%s" OAuth client. Error: %s.' % (client, to_native(e)) )
    
        else:
            for oc in all_oauth_clients['data']:
                client_id = oc['id']
                # Retrieve information for all OAuth tokens
                try:        
                    ret = tfe.call_endpoint(tfe.api.oauth_tokens.list, oauth_client_id=client_id)
                except Exception as e:
                    module.fail_json(msg='Unable to list OAuth Tokens for "%s" OAuth client. Error: %s.' % (client_id, to_native(e)) )
        
                result['json']['data'].extend(ret['data'])           

    module.exit_json(**result)


if __name__ == '__main__':
    main()