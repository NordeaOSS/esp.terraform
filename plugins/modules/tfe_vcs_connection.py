#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Krzysztof Lewandowski <krzysztof.lewandowski@nordea.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: tfe_vcs_connection
short_description: Manage VCS connections in the organization
description:
- Creates or removes a VCS connection between an organization and a VCS provider.
- An OAuth Client represents the connection between an organization and a VCS provider.
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
    - Definition of the attributes for the VCS connection.
    - Required when C(state=present).       
    type: dict
    suboptions:
      service-provider:
        description:
        - The VCS provider being connected with.
        type: str
        choices: [ 'bitbucket_server', 'github', 'github_enterprise', 'gitlab_hosted', 'gitlab_community_edition', 'gitlab_enterprise_edition', 'ado_server' ]
        required: true    
      http-url:
        description:
        - The homepage of your VCS provider.
        type: str
        required: false
      api-url:
        description:
        - The base URL of your VCS provider's API.
        type: str
        required: false
      name:
        description:
        - An optional display name for the OAuth Client. 
        - If left null, the UI will default to the display name of the VCS provider.
        type: str
        required: false
      oauth-token-string:
        description:
        - The token string you were given by your VCS provider.
        type: str
        required: false
      private-key:
        description:
        - The text of the SSH private key associated with your Azure DevOps Server account.
        type: str
        required: false                
  client:
    description:
    - OAuth client (VCS connections) ID or name to remove.
    - Required when C(state=absent).    
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
- name: Create a VCS connection between an organization and a VCS provider
  esp.terraform.tfe_vcs_connection:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    attributes:
      "service-provider": bitbucket_server
      "http-url": https://bitbucket.example.com
      "api-url": https://bitbucket.example.com
      "name": My test VCS
    state: present
    validate_certs: no
  register: _result

- name: Update a VCS connection
  esp.terraform.tfe_vcs_connection:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    client: My test VCS
    attributes:
      "name": My new VCS name
    state: present
    validate_certs: no
  register: _result

- name: Remove a VCS connection between an organization and a VCS provider, refer by its name
  esp.terraform.tfe_vcs_connection:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    client: My test VCS
    state: absent
    validate_certs: no

- name: Remove a VCS connection between an organization and a VCS provider, refer by its ID
  esp.terraform.tfe_vcs_connection:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo    
    client: oc-tVGQD7Wk2ujR9Gvu
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
    description: OAuth Client state
    returned: always
    type: str
    sample: present
json:
    description: Details on OAuth Clients.
    returned: success
    type: dict
    contains:
        data:
            description: Details on OAuth Clients.
            returned: success
            type: dict                  
            sample:
                attributes:
                    api-url: https://bitbucket.example.com
                    callback-url: "https://terraform.example.com/auth/2b81cf18-0e5a-48dc-95aa-cee4a15472b8/callback"
                    connect-path: "/auth/2b81cf18-0e5a-48dc-95aa-cee4a15472b8?organization_id=1"
                    http-url: https://bitbucket.example.com
                    key: 8eebbb1bf0a0f3a3e679fd0fb31b2647
                    name: My test VCS
                    rsa-public-key: "-----BEGIN PUBLIC KEY- .... "
                    service-provider: bitbucket_server
                    service-provider-display-name: Bitbucket Server
                    tfvcs: false
                id: oc-4BWCffCgwSGYCrkW
                relationships:
                    oauth-tokens:
                        data: []
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
        state=dict(type='str', choices=['present', 'absent'], default='present'),
        client=dict(type='str', required=False, no_log=False),
        attributes=dict(
            type='dict', 
            required=False, no_log=False,
            # options=dict(
            #     service-provider=dict(type='str', choices=['bitbucket_server', 'github', 'github_enterprise', 'gitlab_hosted', 'gitlab_community_edition', 'gitlab_enterprise_edition', 'ado_server'], required=True, no_log=False),
            #     http-url=dict(type='str', required=True, no_log=False),
            #     api-url=dict(type='str', required=True, no_log=False),
            #     name=dict(type='str', required=False, no_log=False),
            #     oauth-token-string=dict(type='str', required=False, no_log=False),
            #     private-key=dict(type='str', required=False, no_log=False),
            # ),
        )
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,  
        required_if=[('state', 'absent', ('client',), True), ('state', 'present', ('attributes',), True)],
    )

    tfe = TFEHelper(module)
    
    organization = tfe.get_org_name_when_exists(organization=module.params['organization'])
    state = module.params['state']
    client = module.params['client']
    attributes = module.params['attributes']

    # Seed the result dict in the object
    result = dict(
        changed=False,
        organization=organization,
        state=state,
        json={},
    )
    if client is not None:
        result['client'] = client
    if attributes is not None:
        result['attributes'] = attributes

    # Set organization
    try:        
        tfe.call_endpoint(tfe.api.set_org, org_name=organization)
    except Exception as e:
        module.fail_json(msg='Unable to set "%s" organization to use for org specific endpoints: %s' % (organization, to_native(e)))
    
    # Get the list of all OAuth clients
    try:        
        all_oauth_clients = tfe.call_endpoint(tfe.api.oauth_clients.list)
    except Exception as e:
        module.fail_json(msg='Unable to list OAuth Clients in "%s" organization. Error: %s.' % (organization, to_native(e)) )
    
    # Get existing client ID. 
    client_id = None
    if client is not None:
        # First, try to find OAuth Client by its ID
        if any([oc for oc in all_oauth_clients['data'] if oc['id'] == client]):
            client_id = [oc for oc in all_oauth_clients['data'] if oc['id'] == client][0]['id']
        else:        
            # Next, try to find OAuth Client by its name
            number_of_oauth_clients = len([oc for oc in all_oauth_clients['data'] if oc['attributes']['name'] == client])
            if number_of_oauth_clients > 1:
                module.fail_json(msg='Found multiple OAuth Clients with "%s" name in "%s" organization. Refer to OAuth Client by its ID.' % (client, organization) )
            if number_of_oauth_clients == 1:
                client_id = [oc for oc in all_oauth_clients['data'] if oc['attributes']['name'] == client][0]['id']

        if (client_id is None) and (state == 'present'):
            module.fail_json(msg='The supplied "%s" OAuth Client does not exist in "%s" organization.' % (client, organization) )
    else:
        if 'name' not in attributes:
            module.fail_json(msg='`name` is required when creating a new OAuth Client')
        # Find client_id when 'New' OAuth Client already exists
        if any(oc['attributes']['name'] == attributes['name'] for oc in all_oauth_clients['data']):
            client_id = [oc for oc in all_oauth_clients['data'] if oc['attributes']['name'] == attributes['name']][0]['id']            

    # Remove the OAuth Client if it exists and state == 'absent'
    if (state == 'absent') and (client_id is not None):

        if not module.check_mode:
            try:          
                result['json'] = tfe.call_endpoint(tfe.api.oauth_clients.destroy, client_id=client_id)
            except Exception as e:
                module.fail_json(msg='Unable to remove "%s" OAuth Client in "%s" organization. Error: %s.' % (client, organization, to_native(e)) ) 

        result['changed'] = True
 
    # Update the OAuth Client if it exists and state == 'present'
    if (state == 'present') and (client_id is not None):

        oc_payload = {
          "data": {
            "id": client_id,
            "type": "oauth-clients",
            "attributes": attributes
          }
        }

        # Check if 'attributes' is a subset of current attributes, i.e. if there is any change
        current_attributes = [oc for oc in all_oauth_clients['data'] if oc['id'] == client_id][0]['attributes']            
        if not tfe.is_subset(subset=attributes, superset=current_attributes):

            if not module.check_mode:
                try:        
                    result['json'] = tfe.call_endpoint(tfe.api.oauth_clients.update, client_id=client_id, payload=oc_payload)                
                except Exception as e:
                    module.fail_json(msg='Unable to update "%s" OAuth Client in "%s" organization. Error: %s.' % (client, organization, to_native(e)) )    
                

            result['changed'] = True

        result['json'] = tfe.call_endpoint(tfe.api.oauth_clients.show, client_id=client_id)

    # Create the OAuth Client if it does not exist and state == 'present'
    if (state == 'present') and (client_id is None):

        create_oc_payload = {
          "data": {
            "type": "oauth-clients",
            "attributes": attributes
          }
        }      

        if not module.check_mode:  
            try:        
                result['json'] = tfe.call_endpoint(tfe.api.oauth_clients.create, payload=create_oc_payload)
            except Exception as e:
                module.fail_json(msg='Unable to create OAuth Client in "%s" organization. Error: %s.' % (organization, to_native(e)) )

        result['changed'] = True

    module.exit_json(**result)


if __name__ == '__main__':
    main()