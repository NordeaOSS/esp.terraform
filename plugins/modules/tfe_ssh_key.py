#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Krzysztof Lewandowski <krzysztof.lewandowski@nordea.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: tfe_ssh_key
short_description: Create, update, and delete SSH keys
description:
- Creates, edits or deletes Terraform SSH keys.
- SSH keys can be used in two places, i.e. they can be assigned to VCS provider integrations,
- they can be assigned to workspaces and used when Terraform needs to clone modules from a Git server.
- An SSH key can be referred either by its ID or by its name.
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
  ssh_key:
    description:
    - SSH key to edit or remove.
    - SSH key may be referred either by its id or its name.
    type: str
    required: false    
  attributes:
    description:
    - Definition of the attributes for the SSH key.
    - Required when C(state=present).       
    type: dict
    required: false      
    suboptions:
      name:
        description:
        - A name to identify the SSH key.
        type: str
        required: true    
      value:
        description:
        - The text of the SSH private key
        type: str
        required: false
  state:
    description:
    - Whether the SSH key should exist or not.
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
- name: Create an SSH Key
  esp.terraform.tfe_ssh_key:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo    
    attributes:
      "name": my-ssh-key
      "value": "{{ lookup('file', 'files/private.key') }}"
    state: present
    validate_certs: no

- name: Update an SSH Key
  esp.terraform.tfe_ssh_key:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    ssh_key: my-ssh-key 
    attributes:
      "value": "{{ lookup('file', 'files/new.private.key') }}"
    state: present
    validate_certs: no

- name: Delete an SSH Key (supplied by its name)
  esp.terraform.tfe_ssh_key:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    ssh_key: my-ssh-key
    state: absent
    validate_certs: no

- name: Delete an SSH Key (supplied by its ID)
  esp.terraform.tfe_ssh_key:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    ssh_key: sshkey-1nXFmNCq38FDyUqo
    state: absent
    validate_certs: no    
'''

RETURN = r'''
json:
    description: Details on the SSH key.
    returned: success
    type: dict
    contains:
        data:
            description: Details on the SSH key.
            returned: success
            type: dict                  
            sample:
                attributes:
                    name: my-ssh-key
                id: sshkey-ZUVVrX3Vov4qyWB4
                links:
                    self: /api/v2/ssh-keys/sshkey-ZUVVrX3Vov4qyWB4
                type: ssh-keys          
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_bytes, to_native, to_text

from ansible_collections.esp.terraform.plugins.module_utils.tfe_helper import TFEHelper


def main():
    argument_spec = TFEHelper.tfe_argument_spec()
    argument_spec.update(
        organization=dict(type='str', required=True, no_log=False),      
        ssh_key=dict(type='str', required=False, no_log=False),
        state=dict(type='str', choices=['present', 'absent'], default='present'),
        attributes=dict(
            type='dict', 
            required=False, no_log=False,
        )
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,  
        required_if=[('state', 'absent', ('ssh_key',), True), ('state', 'present', ('attributes',), True)],        
    )

    tfe = TFEHelper(module)

    organization = tfe.get_org_name_when_exists(organization=module.params['organization'])
    ssh_key = module.params['ssh_key']
    state = module.params['state']
    attributes = module.params['attributes']

    # Seed the result dict in the object
    result = dict(
        changed=False,
        state=state,
        organization=organization,
        json={},
    )
    if ssh_key is not None:
        result['ssh_key'] = ssh_key

    # Set organization
    try:        
        tfe.call_endpoint(tfe.api.set_org, org_name=organization)
    except Exception as e:
        module.fail_json(msg='Unable to set "%s" organization to use for org specific endpoints: %s' % (organization, to_native(e)))

    # Get the list of all SSH keys
    try:        
        all_ssh_keys = tfe.call_endpoint(tfe.api.ssh_keys.list)
    except Exception as e:
        module.fail_json(msg='Unable to list SSH keys in "%s" organization. Error: %s.' % (organization, to_native(e)) )

    # Get an existing SSH key ID. 
    ssh_key_id = None
    if ssh_key is not None:
        # Refer to an SSH key by its name
        if any(k['attributes']['name'] == ssh_key for k in all_ssh_keys['data']):
            ssh_key_id = [k for k in all_ssh_keys['data'] if k['attributes']['name'] == ssh_key][0]['id']
        # Refer to an SSH key by its ID
        elif any(k['id'] == ssh_key for k in all_ssh_keys['data']):
            ssh_key_id = ssh_key
        else:
            if state == 'present':
                module.fail_json(msg='The supplied "%s" SSH keys does not exist in "%s" organization.' % (ssh_key, organization) )
    else:
        if 'name' not in attributes:
            module.fail_json(msg='`name` is required when creating a new SSH key')
        # Find ssh_key_id when 'New' SSH key already exists
        if any(k['attributes']['name'] == attributes['name'] for k in all_ssh_keys['data']):
            ssh_key_id = [k for k in all_ssh_keys['data'] if k['attributes']['name'] == attributes['name']][0]['id']

    # Delete the SSH key if it exists and state == 'absent'
    if (state == 'absent') and (ssh_key_id is not None):

        if not module.check_mode:
            try:        
                result['json'] = tfe.call_endpoint(tfe.api.ssh_keys.destroy, ssh_key_id=ssh_key_id)
            except Exception as e:
                module.fail_json(msg='Unable to delete "%s" SSH key in "%s" organization. Error: %s.' % (ssh_key, organization, to_native(e)) )          

        result['changed'] = True
 
    # Update the SSH key if it exists and state == 'present'
    if (state == 'present') and (ssh_key_id is not None):

        if attributes is not None:
            k_payload = {
              "data": {
                "type": "ssh-keys",
                "attributes": attributes
              }
            }

            # Check if 'attributes' is a subset of current attributes, i.e. if there is any change
            current_attributes = [k for k in all_ssh_keys['data'] if k['id'] == ssh_key_id][0]['attributes']
            if not tfe.is_subset(subset=attributes, superset=current_attributes):

                if not module.check_mode:
                    try:        
                        result['json'] = tfe.call_endpoint(tfe.api.ssh_keys.update, ssh_key_id=ssh_key_id, payload=k_payload)
                    except Exception as e:
                        module.fail_json(msg='Unable to update "%s" SSH key in "%s" organization. Error: %s.' % (ssh_key, organization, to_native(e)) )    

                result['changed'] = True

    # Create the SSH key if it does not exist and state == 'present'
    if (state == 'present') and (ssh_key_id is None):

        if 'name' not in attributes:
            module.fail_json(msg='`name` is required when creating a new SSH key')

        k_payload = {
          "data": {
            "type": "ssh-keys",
            "attributes": attributes
          }
        }

        if not module.check_mode:
            try:        
                result['json'] = tfe.call_endpoint(tfe.api.ssh_keys.create, payload=k_payload)
            except Exception as e:
                module.fail_json(msg='Unable to create "%s" SSH key in "%s" organization. Error: %s.' % (ssh_key, organization, to_native(e)) )    

        result['changed'] = True

    module.exit_json(**result)


if __name__ == '__main__':
    main()