#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Krzysztof Lewandowski <krzysztof.lewandowski@nordea.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: tfe_run
short_description: Create, apply, discard or cancel a run
description:
- Creates, applies, discards or cancels a run.
- When creating a run, it takes the workspace’s most recently used configuration version.
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
    - The workspace name or ID to execute a run on.
    type: str
    required: true         
  action:
    description:
    - Type of action to perform on a run.
    type: str
    choices: [ create, apply, discard, cancel, force-cancel, force-execute ]
    required: true    
  attributes:
    description:
    - Definition of the attributes for the run.
    - Required when C(action=create).  
    - When creating a run, it takes the workspace’s most recently used configuration version.  
    type: dict
    required: false      
    suboptions:
      is-destroy:
        description:
        - Specifies if this plan is a destroy plan, which will destroy all provisioned resources.
        type: bool
        default: false    
      message:
        description:
        - Specifies the message to be associated with this run.
        type: str
        required: false  
      refresh:
        description:
        - Specifies whether or not to refresh the state before a plan.
        type: bool
        default: true                                             
      refresh-only:
        description:
        - Whether this run should use the refresh-only plan mode, which will refresh the state without modifying any resources.
        type: bool
        default: false   
      replace-addrs:
        description:
        - Specifies an optional list of resource addresses to be passed to the C(-replace) flag.
        type: list
      target-addrs:
        description:
        - Specifies an optional list of resource addresses to be passed to the C(-target) flag.
        type: list                               
  run:
    description:
    - The run ID to act on.
    - Required when C(action) is C(apply), C(discard), C(cancel), C(force-cancel), C(force-execute).
    type: str
    required: false       
  comment:
    description:
    - An optional comment on the run.
    - Applicable when C(action) is C(apply), C(discard), C(cancel), C(force-cancel), C(force-execute).
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
- name: Perform a plan and optionaly apply if the auto-apply setting is enabled on the workspace
  esp.terraform.tfe_run:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    workspace: bar
    action: create
    attributes:
      "is-destroy": false
      "message": Queued manually via the Terraform Enterprise API    
    validate_certs: no

- name: Apply a run
  esp.terraform.tfe_run:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    workspace: bar
    action: apply
    run: run-CZcmD7eagjhyX0vN
    comment: Applied via the Terraform Enterprise API
    validate_certs: no

- name: Cancel a run
  esp.terraform.tfe_run:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    workspace: bar
    action: cancel
    run: run-CZcmD7eagjhyX0vN
    comment: Cancelled via the Terraform Enterprise API
    validate_certs: no

- name: Create a destroy plan - destroy all provisioned resources
  esp.terraform.tfe_run:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    workspace: bar
    action: create
    attributes:
      "is-destroy": true
      "message": Destroy all provisioned resources
    validate_certs: no
'''

RETURN = r'''
json:
    description: Details on the run.
    returned: success
    type: dict
    contains:
        data:
            description: Details on the run.
            returned: success
            type: dict                  
            sample:
                attributes:
                    actions:
                        is-cancelable: true
                        is-confirmable: false
                        is-discardable: false
                        is-force-cancelable: false
                    canceled-at: null
                    created-at: 2021-06-30T20:48:44.319Z
                    has-changes: false
                    is-destroy: false
                    message: Queued manually via the Terraform Enterprise API
                    permissions:
                        can-apply: true
                        can-cancel: true
                        can-comment: true
                        can-discard: true
                        can-force-cancel: true
                        can-force-execute: true
                        can-override-policy-check: true
                    plan-only: false
                    source: tfe-api
                    status: pending
                    status-timestamps:
                        plan-queueable-at: 2021-06-30T20:48:44+00:00
                    target-addrs: null
                    trigger-reason: manual
                id: run-xvoeNhZRn5U1uEcf
                links:
                    self: /api/v2/runs/run-xvoeNhZRn5U1uEcf
                relationships:
                    apply:
                        data:
                            id: apply-WYLWbu8jLcnngfmF
                            type: applies
                        links:
                            related: /api/v2/runs/run-xvoeNhZRn5U1uEcf/apply
                    plan:
                        data:
                            id: plan-nx55vouUHb7VrPVa
                            type: plans
                        links:
                            related: /api/v2/runs/run-xvoeNhZRn5U1uEcf/plan
                    workspace:
                        data:
                            id: ws-xt1dqgiDPEZpJazo
                            type: workspaces
                type: runs         
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_bytes, to_native, to_text

from ansible_collections.esp.terraform.plugins.module_utils.tfe_helper import TFEHelper


def main():
    argument_spec = TFEHelper.tfe_argument_spec()
    argument_spec.update(
        organization=dict(type='str', required=True, no_log=False),
        workspace=dict(type='str', required=True, no_log=False),     
        run=dict(type='str', required=False, no_log=False),
        action=dict(type='str', required=True, choices=['create', 'apply', 'discard', 'cancel', 'force-cancel', 'force-execute'], no_log=False),
        attributes=dict(
            type='dict', 
            required=False, no_log=False,
        ),
        comment=dict(type='str', required=False, no_log=False),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,  
        required_if=[('action', 'apply', ('run',), True), 
                     ('action', 'discard', ('run',), True),
                     ('action', 'cancel', ('run',), True),
                     ('action', 'force-cancel', ('run',), True),
                     ('action', 'force-execute', ('run',), True),
                     ('action', 'create', ('attributes',), True)],        
    )

    tfe = TFEHelper(module)

    organization = tfe.get_org_name_when_exists(organization=module.params['organization'])
    workspace = module.params['workspace']
    run = module.params['run']
    action = module.params['action']
    comment = module.params['comment']
    attributes = module.params['attributes']

    # Seed the result dict in the object
    result = dict(
        changed=False,
        action=action,
        organization=organization,
        workspace=workspace,
        json={},
    )
    if run is not None:
        result['run'] = run
    if comment is not None:
        result['comment'] = comment        
    if attributes is not None:
        result['attributes'] = attributes.copy()

    # Set organization
    try:        
        tfe.call_endpoint(tfe.api.set_org, org_name=organization)
    except Exception as e:
        module.fail_json(msg='Unable to set "%s" organization to use for org specific endpoints: %s' % (organization, to_native(e)))

    # Get the list of all workspaces without additional details
    try:        
        all_workspaces = tfe.call_endpoint(tfe.api.workspaces.list_all, include=None)
    except Exception as e:
        module.fail_json(msg='Unable to list workspaces in "%s" organization. Error: %s.' % (organization, to_native(e)) )

    # Get existing workspace ID. 
    workspace_id = None
    # Refer to a workspace by its name
    if any(w['attributes']['name'] == workspace for w in all_workspaces['data']):
        workspace_id = [w for w in all_workspaces['data'] if w['attributes']['name'] == workspace][0]['id']
    # Refer to a workspace by its ID
    elif any(w['id'] == workspace for w in all_workspaces['data']):
        workspace_id = workspace
    else:
        module.fail_json(msg='The supplied "%s" workspace does not exist in "%s" organization.' % (workspace, organization) )
 
    # Create a run
    if (action == 'create'):

        if (attributes is None) or ('message' not in attributes):
              attributes['message'] = "Queued manually via the Terraform Enterprise API"

        r_payload ={
          "data": {
            "attributes": attributes,
            "type": "runs",
            "relationships": {
              "workspace": {
                "data": {
                  "type": "workspaces",
                  "id": workspace_id
                }
              }
            }
          }
        }

        if not module.check_mode:
            try:        
                result['json'] = tfe.call_endpoint(tfe.api.runs.create, payload=r_payload)
            except Exception as e:
                module.fail_json(msg='Unable to create a run in "%s" workspace. Error: %s.' % (workspace, to_native(e)) )    

        result['changed'] = True

    # Apply/Discard/Cancel/Force-cancel a plan
    if action in ['apply', 'discard', 'cancel', 'force-cancel', 'force-execute']:

        # Check if the run exists
        try:        
            tfe.call_endpoint(tfe.api.runs.show, run_id=run, include=None)
        except Exception as e:
            module.fail_json(msg='Unable to retrieve details on a run in "%s" workspace. Error: %s.' % (workspace, to_native(e)) )

        r_payload = {}
        if comment is not None:
            r_payload = {
              "comment": comment
            }

        if not module.check_mode:
            try:        
                if action == 'apply':
                  tfe.call_endpoint(tfe.api.runs.apply, run_id=run, payload=r_payload)
                if action == 'discard':
                  tfe.call_endpoint(tfe.api.runs.discard, run_id=run, payload=r_payload)
                if action == 'cancel':
                  tfe.call_endpoint(tfe.api.runs.cancel, run_id=run, payload=r_payload)
                if action == 'force-cancel':
                  tfe.call_endpoint(tfe.api.runs.force_cancel, run_id=run, payload=r_payload)                
                if action == 'force-execute':
                  tfe.call_endpoint(tfe.api.runs.force_execute, run_id=run)                   
            except Exception as e:
                module.fail_json(msg='Unable to "%s" "%s" run in "%s" workspace. Error: %s.' % (action, run, workspace, to_native(e)) )    

        # Get details of the run
        try:        
            result['json'] = tfe.call_endpoint(tfe.api.runs.show, run_id=run, include=['plan', 'apply'])
        except Exception as e:
            module.fail_json(msg='Unable to retrieve details on a run in "%s" workspace. Error: %s.' % (workspace, to_native(e)) )

        result['changed'] = True

    module.exit_json(**result)


if __name__ == '__main__':
    main()