#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Krzysztof Lewandowski <krzysztof.lewandowski@nordea.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: tfe_ssh_key_info
short_description: List SSH keys in the organization
description:
- Lists SSH keys in the organization.
- SSH keys can be used in two places, i.e. they can be assigned to VCS provider integrations,
- they can be assigned to workspaces and used when Terraform needs to clone modules from a Git server.
- The list provide metadata about SSH keys. The actual private key text is write-only, and Terraform Cloud never provides it to users.
- Details on an SSH key can be retrieved either by its ID or by its name.
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
    - List of SSH keys to retrieve details for.
    - This can be '*' which means all SSH keys.
    - One may refer to an SSH key either by its ID or its assigned name.
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
- name: Retrieve details on all SSH keys in the organization
  esp.terraform.tfe_ssh_key_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    ssh_key:
      - '*'
    validate_certs: no
  register: _result

- name: Retrieve details on the given SSH keys (supplied by names or IDs), in the organization
  esp.terraform.tfe_ssh_key_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    ssh_key:
      - my-ssh-key
      - sshkey-1nXFmNCq38FDyUqo
    validate_certs: no
  register: _result
'''

RETURN = r'''
json:
    description: Details on teams.
    returned: success
    type: dict
    contains:
        data:
            description: Details on teams.
            returned: success
            type: list
            elements: dict                    
            sample:
                - attributes:
                      name: my-ssh-key
                  id: sshkey-1nXFmNCq38FDyUqo
                  links:
                      self: /api/v2/ssh-keys/sshkey-1nXFmNCq38FDyUqo
                  type: ssh-keys             
'''

import collections

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_bytes, to_native, to_text

from ansible_collections.esp.terraform.plugins.module_utils.tfe_helper import TFEHelper


def main():
    argument_spec = TFEHelper.tfe_argument_spec()
    argument_spec.update(
        organization=dict(type='str', required=True, no_log=False),
        ssh_key=dict(type='list', elements='str', no_log=False, default=[ '*' ]),         
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,    
    )

    tfe = TFEHelper(module)
    
    organization = tfe.get_org_name_when_exists(organization=module.params['organization'])

    # Parse `ssh_key` parameter and create list of SSH keys.
    # It's possible someone passed a comma separated string, so we should handle that.
    # This can be either an empty list or '*' which means all SSH keys.
    ssh_keys = module.params['ssh_key']
    if isinstance(module.params['ssh_key'], collections.Iterable):
        ssh_keys = [p.strip() for p in module.params['ssh_key']]
        ssh_keys = tfe.listify_comma_sep_strings_in_list(ssh_keys)
    if not ssh_keys:
        ssh_keys = [ '*' ]

    # Seed the result dict in the object
    result = dict(
        changed=False,
        organization=organization,
        ssh_keys=ssh_keys,
        json={},
    )

    # Set organization
    try:        
        tfe.call_endpoint(tfe.api.set_org, org_name=organization)
    except Exception as e:
        module.fail_json(msg='Unable to set "%s" organization to use for org specific endpoints: %s' % (organization, to_native(e)))
    
    if '*' in ssh_keys:
        # Retrieve information for all SSH keys
        try:        
            result['json'] = tfe.call_endpoint(tfe.api.ssh_keys.list)
        except Exception as e:
            module.fail_json(msg='Unable to list SSH keys in "%s" organization. Error: %s.' % (organization, to_native(e)) )
    else:
        result['json']['data'] = []
        # First, get the list of all SSH keys
        try:        
            all_ssh_keys = tfe.call_endpoint(tfe.api.ssh_keys.list)
        except Exception as e:
            module.fail_json(msg='Unable to list SSH keys in "%s" organization. Error: %s.' % (organization, to_native(e)) )

        # Next, iterate over the supplied SSH keys to retrieve their details
        for ssh_key in ssh_keys:

            # Refer to an SSH key by its name
            if any(k['attributes']['name'] == ssh_key for k in all_ssh_keys['data']):
                try:
                    ssh_key_id = [k for k in all_ssh_keys['data'] if k['attributes']['name'] == ssh_key][0]['id']
                    ret = tfe.call_endpoint(tfe.api.ssh_keys.show, ssh_key_id=ssh_key_id)
                except Exception as e:
                    module.fail_json(msg='Unable to retrieve details on a SSH key in "%s" organization. Error: %s.' % (organization, to_native(e)) )

            # Refer to an SSH key by its ID
            else:
                try:        
                    ret = tfe.call_endpoint(tfe.api.ssh_keys.show, ssh_key_id=ssh_key)
                except Exception as e:
                    module.fail_json(msg='Unable to retrieve details on a SSH key in "%s" organization. Error: %s.' % (organization, to_native(e)) )

            result['json']['data'].append(ret['data'])           

    module.exit_json(**result)


if __name__ == '__main__':
    main()