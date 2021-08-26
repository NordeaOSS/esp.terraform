#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Krzysztof Lewandowski <krzysztof.lewandowski@nordea.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: tfe_workspace
short_description: Create, update, and destroy Terraform workspaces
description:
- Creates, updates or removes Terraform workspaces.
- Workspaces represent running infrastructure managed by Terraform.
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
  workspace:
    description:
    - The workspace to edit or remove.
    - The workspace may be referred either by its id or its name.
    type: str
    required: false
  attributes:
    description:
    - Definition of the workspace properties.
    - Required when C(state=present).       
    type: dict
    required: false      
    suboptions:
      name:
        description:
        - The name of the workspace, which can only include letters, numbers, -, and _. 
        - This will be used as an identifier and must be unique in the organization.
        type: str
        required: true    
      agent-pool-id:
        description:
        - Required when C(execution-mode=agent). The ID of the agent pool belonging to the workspace's organization. 
        - This value must not be specified if C(execution-mode=remote) or C(execution-mode=local) or if C(operations=true).
        type: str
        required: false
      allow-destroy-plan:
        description:
        - Whether destroy plans can be queued on the workspace.
        type: bool
        required: false
        default: true
      auto-apply:
        description:
        - Whether to automatically apply changes when a Terraform plan is successful.
        type: bool
        required: false
        default: false
      description:
        description:
        - A description for the workspace.
        type: str
        required: false
      execution-mode:
        description:
        - Which execution mode to use. Valid values are C(remote), C(local), and C(agent). 
        - When set to C(local), the workspace will be used for state storage only. 
        - This value must not be specified if C(operations) is specified.
        type: str
        required: false
        default: remote
      file-triggers-enabled:
        description:
        - Whether to filter runs based on the changed files in a VCS push. 
        - If enabled, the C(working-directory) and C(trigger-prefixes) describe a set of paths which must contain changes for a VCS push to trigger a run. 
        - If disabled, any push will trigger a run.
        type: bool
        required: false
        default: true
      global-remote-state:
        description:
        - Whether the workspace should allow all workspaces in the organization to access its state data during runs. 
        - If C(false), then only specifically approved workspaces can access its state. 
        type: bool
        required: false
        default: false
      queue-all-runs:
        description:
        - Whether runs should be queued immediately after workspace creation. 
        - When set to C(false), runs triggered by a VCS change will not be queued until at least one run is manually queued. 
        type: bool
        required: false
        default: false
      source-name:
        description:
        - A friendly name for the application or client creating this workspace. 
        - If set, this will be displayed on the workspace as "Created via C(source-name)".
        type: str
        required: false
      source-url:
        description:
        - A URL for the application or client creating this workspace. 
        - This can be the URL of a related resource in another app, or a link to documentation or other info about the client.
        type: str
        required: false
      speculative-enabled:
        description:
        - Whether this workspace allows automatic speculative plans. 
        - Setting this to false prevents Terraform Cloud from running plans on pull requests, 
        - which can improve security if the VCS repository is public or includes untrusted contributors. 
        - It doesn't prevent manual speculative plans via the remote backend or the runs API. 
        type: bool
        required: false
        default: true
      terraform-version:
        description:
        - The version of Terraform to use for this workspace. 
        - Upon creating a workspace, the latest version is selected unless otherwise specified.
        type: str
        required: false
      trigger-prefixes:
        description:
        - List of repository-root-relative paths which should be tracked for changes, in addition to the working directory.
        type: list
        required: false
      vcs-repo:
        description:
        - Settings for the workspace's VCS repository. 
        - If omitted, the workspace is created without a VCS repo. 
        - If included, you must specify at least the C(oauth-token-id) and C(identifier) keys below.
        type: dict
        required: false
        suboptions:
          oauth-token-id:
            description:
            - The VCS Connection (OAuth Connection + Token) to use.
            type: str
            required: true 
          branch:
            description:
            - The repository branch that Terraform will execute from. 
            - If omitted or submitted as an empty string, this defaults to the repository's default branch.
            type: str
            required: false 
          ingress-submodules:
            description:
            - Whether submodules should be fetched when cloning the VCS repository.
            type: bool
            required: false 
            default: false
          identifier:
            description:
            - A reference to your VCS repository in the format :org/:repo where :org and :repo refer to the organization and repository in your VCS provider.
            type: str
            required: false 
      working-directory:
        description:
        - A relative path that Terraform will execute within. 
        - This defaults to the root of your repository and is typically set to a subdirectory matching the environment 
        - when multiple environments exist within the same repository.
        type: str
        required: false
  state:
    description:
    - Whether the workspace should exist or not.
    type: str
    default: present
    choices: [ absent, present ]
    required: true
  locked:
    description:
      - C(true) locks the workspace. Optionally, you may provide C(lock_reason).
      - C(false) unlocks the workspace.
    type: bool
    required: false
  lock_reason:
    description:
    - The reason for locking the workspace.
    - Can only be specified together with C(locked=true).
    type: str
    required: false
  ssh_key:
    description:
    - The SSH key to assign to the workspace.
    - The SSH key may be referred either by its ID or its name.
    - Empty string C("") unassigns the currently assigned SSH key from the workspace.
    type: str
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
- name: Create a Workspace
  esp.terraform.tfe_workspace:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo    
    attributes:
      "name": my-workspace
      "auto-apply": true
      "vcs-repo":
        "oauth-token-id": ot-afSmwHZXwLDY1wSs
        "identifier": "PROJECT/terraform-project-repo"
        "branch": ""
        "ingress-submodules": false
      "source-name": Ansible
    state: present
    validate_certs: no

- name: Edit a workspace
  esp.terraform.tfe_workspace:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    workspace: my-workspace 
    attributes:
      "name": new-workspace-name
      "auto-apply": false
      "working-directory": "/tfe"
    state: present
    validate_certs: no

- name: Edit and lock a workspace
  esp.terraform.tfe_workspace:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    workspace: my-workspace 
    attributes:
      "auto-apply": false
    locked: true
    lock_reason: Prevent Terraform runs
    state: present
    validate_certs: no

- name: Unlock a workspace
  esp.terraform.tfe_workspace:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    workspace: my-workspace 
    locked: false
    state: present
    validate_certs: no

- name: Assign an SSH key to a workspace
  esp.terraform.tfe_workspace:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    workspace: my-workspace 
    ssh_key: my-ssh-key
    #ssh_key: sshkey-1nXFmNCq38FDyUqo
    state: present
    validate_certs: no

- name: Unassign an SSH key from a workspace
  esp.terraform.tfe_workspace:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    workspace: my-workspace 
    ssh_key: ''
    state: present
    validate_certs: no

- name: Delete a workspace
  esp.terraform.tfe_workspace:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    workspace: my-workspace
    state: absent
    validate_certs: no
'''

RETURN = r'''
state:
    description: Workspace state
    returned: always
    type: str
    sample: present
json:
    description: Details on workspace.
    returned: success
    type: dict
    contains:
        data:
            description: Details on workspace.
            returned: success
            type: dict                  
            sample:
                attributes:
                    actions:
                        is-destroyable: true
                    allow-destroy-plan: true
                    auto-apply: false
                    auto-destroy-at: null
                    created-at: 2021-05-14T19:42:38.472Z
                    description: null
                    environment: default
                    execution-mode: remote
                    file-triggers-enabled: true
                    global-remote-state: true
                    latest-change-at: 2021-05-14T19:42:38.472Z
                    locked: false
                    name: my-workspace
                    operations: true
                    permissions:
                        can-create-state-versions: true
                        can-destroy: true
                        can-force-unlock: true
                        can-lock: true
                        can-queue-apply: true
                        can-queue-destroy: true
                        can-queue-run: true
                        can-read-settings: true
                        can-read-state-versions: true
                        can-read-variable: true
                        can-unlock: true
                        can-update: true
                        can-update-variable: true
                    queue-all-runs: false
                    source: tfe-api
                    source-name: null
                    source-url: null
                    speculative-enabled: true
                    terraform-version: 0.15.1
                    trigger-prefixes: []
                    vcs-repo:
                        branch: 
                        display-identifier: PROJECT/terraform-project-repo
                        identifier: PROJECT/terraform-project-repo
                        ingress-submodules: false
                        oauth-token-id: ot-afSmwHZXwLDY1wSs
                        repository-http-url: 
                        service-provider: bitbucket_server
                    vcs-repo-identifier: PROJECT/terraform-project-repo
                    working-directory: null
                id: ws-u6asykQpV8EKthKw
                links:
                    self: /api/v2/organizations/foo/workspaces/my-workspace
                relationships:
                    current-configuration-version:
                        data:
                            id: cv-wM6HoLCzt67LPk7p
                            type: configuration-versions
                        links:
                            related: /api/v2/configuration-versions/cv-wM6HoLCzt67LPk7p
                    current-run:
                        data: null
                    current-state-version:
                        data: null
                    latest-run:
                        data: null
                    organization:
                        data:
                            id: foo
                            type: organizations
                    remote-state-consumers:
                        links:
                            related: /api/v2/workspaces/ws-u6asykQpV8EKthKw/relationships/remote-state-consumers
                type: workspaces              
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_bytes, to_native, to_text

from ansible_collections.esp.terraform.plugins.module_utils.tfe_helper import TFEHelper


def main():
    argument_spec = TFEHelper.tfe_argument_spec()
    argument_spec.update(
        organization=dict(type='str', required=True, no_log=False),      
        workspace=dict(type='str', required=False, no_log=False),
        state=dict(type='str', choices=['present', 'absent'], default='present'),
        locked=dict(type='bool', required=False, no_log=False, default=None),
        lock_reason=dict(type='str', required=False, no_log=False),
        ssh_key=dict(type='str', required=False, no_log=False),
        attributes=dict(
            type='dict', 
            required=False, no_log=False,
        )
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True, 
        required_if=[('state', 'absent', ('workspace',), True), ('state', 'present', ('attributes', 'locked', 'ssh_key'), True), ('locked', True, ('lock_reason',), True)], 
    )

    tfe = TFEHelper(module)

    organization = tfe.get_org_name_when_exists(organization=module.params['organization'])
    workspace = module.params['workspace']
    state = module.params['state']
    attributes = module.params['attributes']
    locked = module.params['locked']
    ssh_key = module.params['ssh_key']

    # Seed the result dict in the object
    result = dict(
        changed=False,
        state=state,
        organization=organization,
        json={},
    )
    if workspace is not None:
        result['workspace'] = workspace
    if attributes is not None:
        result['attributes'] = attributes

    # Set organization
    try:        
        tfe.call_endpoint(tfe.api.set_org, org_name=organization)
    except Exception as e:
        module.fail_json(msg='Unable to set "%s" organization to use for org specific endpoints: %s' % (organization, to_native(e)))

    # Get the list of all workspaces
    try:        
        all_workspaces = tfe.call_endpoint(tfe.api.workspaces.list_all, include=None)
    except Exception as e:
        module.fail_json(msg='Unable to list workspaces in "%s" organization. Error: %s.' % (organization, to_native(e)) )

    # Get existing workspace ID. 
    workspace_id = None
    if workspace is not None:
        # Refer to a workspace by its name
        if any(w['attributes']['name'] == workspace for w in all_workspaces['data']):
            workspace_id = [w for w in all_workspaces['data'] if w['attributes']['name'] == workspace][0]['id']
        # Refer to a workspace by its ID
        elif any(w['id'] == workspace for w in all_workspaces['data']):
            workspace_id = workspace
        else:
            if state == 'present':
                module.fail_json(msg='The supplied "%s" workspace does not exist in "%s" organization.' % (workspace, organization) )
    else:
        if 'name' not in attributes:
            module.fail_json(msg='`name` is required when creating a new workspace')
        # Find workspace_id when 'New' workspace already exists
        if any(w['attributes']['name'] == attributes['name'] for w in all_workspaces['data']):
            workspace_id = [w for w in all_workspaces['data'] if w['attributes']['name'] == attributes['name']][0]['id']

    # Destroy the workspace if it exists and state == 'absent'
    if (state == 'absent') and (workspace_id is not None):

        if not module.check_mode:
            try:        
                result['json'] = tfe.call_endpoint(tfe.api.workspaces.destroy, workspace_id=workspace_id)
            except Exception as e:
                module.fail_json(msg='Unable to destroy "%s" workspace in "%s" organization. Error: %s.' % (workspace, organization, to_native(e)) )          

        result['changed'] = True
 
    # Update the workspace if it exists and state == 'present'
    if (state == 'present') and (workspace_id is not None):

        if attributes is not None:
            w_payload = {
              "data": {
                "type": "workspaces",
                "attributes": attributes
              }
            }

            # Check if 'attributes' is a subset of current attributes, i.e. if there is any change
            current_attributes = [w for w in all_workspaces['data'] if w['id'] == workspace_id][0]['attributes']            
            if not tfe.is_subset(subset=attributes, superset=current_attributes):

                if not module.check_mode:
                    try:        
                        result['json'] = tfe.call_endpoint(tfe.api.workspaces.update, workspace_id=workspace_id, payload=w_payload)
                    except Exception as e:
                        module.fail_json(msg='Unable to update "%s" workspace in "%s" organization. Error: %s.' % (workspace, organization, to_native(e)) )    

                result['changed'] = True

        # Process 'locked' param
        if locked is not None:
            currently_locked = [w for w in all_workspaces['data'] if w['id'] == workspace_id][0]['attributes']['locked']

            # Lock the workspace
            if locked and not currently_locked:
                w_payload = {
                  "reason": module.params['lock_reason'] or ""
                }    

                if not module.check_mode:
                    try:        
                        result['json'] = tfe.call_endpoint(tfe.api.workspaces.lock, workspace_id=workspace_id, payload=w_payload)
                    except Exception as e:
                        module.fail_json(msg='Unable to lock "%s" workspace in "%s" organization. Error: %s.' % (workspace, organization, to_native(e)) )    

                result['changed'] = True            

            # Unlock the workspace
            if not locked and currently_locked:
  
                if not module.check_mode:
                    try:        
                        result['json'] = tfe.call_endpoint(tfe.api.workspaces.unlock, workspace_id=workspace_id)
                    except Exception as e:
                        module.fail_json(msg='Unable to unlock "%s" workspace in "%s" organization. Error: %s.' % (workspace, organization, to_native(e)) )    

                result['changed'] = True  

        # Process 'ssh_key' param
        if ssh_key is not None:
            # Get the list of all SSH keys
            try:        
                all_ssh_keys = tfe.call_endpoint(tfe.api.ssh_keys.list)
            except Exception as e:
                module.fail_json(msg='Unable to list SSH keys in "%s" organization. Error: %s.' % (organization, to_native(e)) )

            if ssh_key:
                # Refer to a SSH key by its name
                if any(k['attributes']['name'] == ssh_key for k in all_ssh_keys['data']):
                    ssh_key_id = [k for k in all_ssh_keys['data'] if k['attributes']['name'] == ssh_key][0]['id']
                elif any(k['id'] == ssh_key for k in all_ssh_keys['data']):
                    ssh_key_id = ssh_key
                else:
                    module.fail_json(msg='The supplied "%s" SSH key does not exist in "%s" organization.' % (ssh_key, organization) )
            else:
                ssh_key_id = None

            currently_assigned_ssh_key = [w for w in all_workspaces['data'] if w['id'] == workspace_id][0]['relationships'].get('ssh-key', {}).get('data', {}).get('id', None)

            # Assign an SSH key to a workspace
            if ssh_key_id is not None and (currently_assigned_ssh_key is None or currently_assigned_ssh_key != ssh_key_id):
                w_payload = {
                  "data": {
                    "attributes": {
                      "id": ssh_key_id
                    },
                    "type": "workspaces"
                  }
                }  

                if not module.check_mode:
                    try:        
                        result['json'] = tfe.call_endpoint(tfe.api.workspaces.assign_ssh_key, workspace_id=workspace_id, payload=w_payload)
                    except Exception as e:
                        module.fail_json(msg='Unable to assign "%s" SSH key to "%s" workspace. Error: %s.' % (ssh_key, workspace, to_native(e)) )    

                result['changed'] = True            

            # Unassign an SSH key from a workspace
            if ssh_key_id is None and currently_assigned_ssh_key is not None:
  
                w_payload = {
                  "data": {
                    "attributes": {
                      "id": None
                    },
                    "type": "workspaces"
                  }
                }

                if not module.check_mode:
                    try:        
                        result['json'] = tfe.call_endpoint(tfe.api.workspaces.unassign_ssh_key, workspace_id=workspace_id, payload=w_payload)
                    except Exception as e:
                        module.fail_json(msg='Unable to unassign "%s" SSH key from "%s" workspace. Error: %s.' % (ssh_key, workspace, to_native(e)) )    

                result['changed'] = True  

    # Create the workspace if it does not exist and state == 'present'
    if (state == 'present') and (workspace_id is None):

        if 'name' not in attributes:
            module.fail_json(msg='`name` is required when creating a new workspace')

        w_payload = {
          "data": {
            "type": "workspaces",
            "attributes": attributes
          }
        }

        if not module.check_mode:
            try:        
                result['json'] = tfe.call_endpoint(tfe.api.workspaces.create, payload=w_payload)
            except Exception as e:
                module.fail_json(msg='Unable to create "%s" workspace in "%s" organization. Error: %s.' % (workspace, organization, to_native(e)) )    

        result['changed'] = True

    module.exit_json(**result)


if __name__ == '__main__':
    main()