#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Krzysztof Lewandowski <krzysztof.lewandowski@nordea.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: tfe_run_info
short_description: List Runs in a Workspace
description:
- Lists Runs in a Workspace.
- A run performs a plan and apply, using a configuration version and the workspace’s current variables.
- A run may be referred either by its id or a custom message associated with it.
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
    - The Workspace name or ID.
    type: str
    required: true    
  run:
    description:
    - List of runs to retrieve details for.
    - This can be '*' which means all runs.
    - One may refer to a run either by its ID or a custom message associated with it.
    type: list
    required: false
    default: [ '*' ]
  include:
    description:
    - Return additional information about nested resources.
    - This can be any of plan, apply, created_by, cost_estimate, configuration_version, configuration_version.ingress_attributes.
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
- name: Retrieve details on all runs in the workspace
  esp.terraform.tfe_run_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    workspace: bar
    run:
      - '*'
    validate_certs: no
  register: _result

# Retrieve details on given runs, include additional information about plan, apply and the commit information used in the run
- name: Retrieve details on given runs (supplied by IDs or custom message)
  esp.terraform.tfe_run_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    workspace: bar
    run:
      - run-EXKqPDacyxFmsDSG
      - Custom message
    include:
      - plan
      - apply
      - configuration_version.ingress_attributes      
    validate_certs: no
  register: _result

- name: Retrieve details on given runs supplied by custom message with filters
  esp.terraform.tfe_run_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    workspace: bar
    run:
      - Custom message
    filter:
      "ingress-attributes":
        "sender-username": 
          - "asmith"
      "configuration-versions":
        "source": 
          - "bitbucket"     
    validate_certs: no
  register: _result

- name: Retrieve details on all runs in the workspace matching the supplied filters (e.g. commit hash)
  esp.terraform.tfe_run_info:
    url: 'https://terraform.example.com'
    token: '{{ token }}'
    organization: foo
    workspace: bar
    run:
      - '*'
    filter:
      "ingress-attributes":
        "commit-sha": 
          - "42e4f31168aa82089aa8ee47c3f9ef74ae85f2e0"
    validate_certs: no
  register: _result

'''

RETURN = r'''
organization:
    description: Organization name or external-id.
    returned: always
    type: str
    sample: foo
workspace:
    description: The Workspace name or ID.
    returned: always
    type: str
    sample: bar
json:
    description: Details on runs.
    returned: success
    type: dict
    contains:
        data:
            description: Details on runs.
            returned: success
            type: list
            elements: dict            
            sample:
                - attributes:
                      actions:
                          is-cancelable: false
                          is-confirmable: false
                          is-discardable: false
                          is-force-cancelable: false
                      canceled-at: null
                      created-at: 2021-06-07T07:07:53.003Z
                      has-changes: true
                      is-destroy: false
                      message: Trigger Terraforom run
                      permissions:
                          can-apply: true
                          can-cancel: true
                          can-comment: true
                          can-discard: true
                          can-force-cancel: true
                          can-force-execute: true
                          can-override-policy-check: true
                      plan-only: false
                      source: tfe-configuration-version
                      status: applied
                      status-timestamps:
                          applied-at: 2021-06-07T07:08:39+00:00
                          apply-queued-at: 2021-06-07T07:08:27+00:00
                          applying-at: 2021-06-07T07:08:28+00:00
                          confirmed-at: 2021-06-07T07:08:27+00:00
                          plan-queueable-at: 2021-06-07T07:07:53+00:00
                          plan-queued-at: 2021-06-07T07:07:53+00:00
                          planned-at: 2021-06-07T07:08:27+00:00
                          planning-at: 2021-06-07T07:07:54+00:00
                      target-addrs: null
                      trigger-reason: disabled
                  id: run-EXKqPDacyxFmsDSG
                  links:
                      self: /api/v2/runs/run-EXKqPDacyxFmsDSG
                  relationships:
                      apply:
                          data:
                              id: apply-bx588DVKD5qiE6Hv
                              type: applies
                          links:
                              related: /api/v2/runs/run-EXKqPDacyxFmsDSG/apply
                      configuration-version:
                          data:
                              id: cv-CnoEnhBDeZaNKN2f
                              type: configuration-versions
                          links:
                              related: /api/v2/runs/run-EXKqPDacyxFmsDSG/configuration-version
                      plan:
                          data:
                              id: plan-E8CDDebTtUSeJPJu
                              type: plans
                          links:
                              related: /api/v2/runs/run-EXKqPDacyxFmsDSG/plan
                      workspace:
                          data:
                              id: ws-xt1dqgiDPEZpJazo
                              type: workspaces
                  type: runs
        included:
            description: Additional information about nested resources.
            returned: success
            type: list
            elements: dict 
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_bytes, to_native, to_text
from ansible.module_utils.six import PY3, PY2, iteritems, string_types

from ansible_collections.esp.terraform.plugins.module_utils.tfe_helper import TFEHelper


def restrict_results(filter=None, result_input=None):
    """
    Restricts results (run details) to those with the matching filter values.
    Returns results dictionary with filtered data.

    """
    # Seed the output result dict
    result_ouput = dict( data=[], included=[] )

    # First, iterate over 'included' resources to find those matching the supplied filters
    for resource_type, resource_attributes in iteritems(filter):
        for included_item in result_input['included']:
            if included_item.get('type', None) == resource_type and isinstance(resource_attributes, dict):

                # Once matching resource type if found, iterate over provided dict keys of the given resource type.
                #  The key might be either an 'id' of the resource ..
                #  .. or one of the resource attribute name - so we should handle both cases
                for attribute_name, attribute_value_list in iteritems(resource_attributes):
                    if attribute_name == 'id' and any(a == included_item.get('id', None) for a in attribute_value_list):
                        result_ouput['included'].append(included_item)
                    if attribute_name != 'id' and any(a == included_item['attributes'].get(attribute_name, None) for a in attribute_value_list):
                        result_ouput['included'].append(included_item)

    # Once all matching 'included' resources are identified, we need to find all their 'parent' and 'grand-parent' (etc) resources
    # to form a complete list of dependencies
    relationships_found = True
    while relationships_found:
        relationships_found = False

        for included_item in result_input['included']:
            for rk, rv in iteritems( included_item.get('relationships', None)):
                if isinstance(rv.get('data', []), list):
                    rv_list = rv.get('data', [])
                else:
                    rv_list = [ rv['data'] ]

                for parent_resource in rv_list:
                    if any(ri['id'] == parent_resource['id'] for ri in result_ouput['included']) and not any(ri['id'] == included_item['id'] for ri in result_ouput['included']):
                        result_ouput['included'].append(included_item)
                        relationships_found = True

    # Finally, we need to search for all runs (i.e. 'data' list) matching identified dependant resources from result_ouput['included'] list created above
    for run_item in result_input['data']:
        for rk, rv in iteritems( run_item.get('relationships', None)):
            if isinstance(rv.get('data', []), list):
                rv_list = rv.get('data', [])
            else:
                rv_list = [ rv['data'] ]

            for child_resource in rv_list:
                if any(ri['id'] == child_resource['id'] for ri in result_ouput['included']):
                    # Add matching 'run' details item the the output list
                    result_ouput['data'].append(run_item)

    return result_ouput


def main():
    argument_spec = TFEHelper.tfe_argument_spec()
    argument_spec.update(
        organization=dict(type='str', required=True, no_log=False),
        workspace=dict(type='str', required=True, no_log=False),
        run=dict(type='list', elements='str', no_log=False, default=[ '*' ]),
        include=dict(type='list', elements='str', no_log=False, required=False, choices=['plan', 'apply', 'created_by', 'cost_estimate', 'configuration_version', 'configuration_version.ingress_attributes']),
        filter=dict(
            type='dict', 
            required=False, no_log=False,
        ),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,    
    )

    tfe = TFEHelper(module)

    organization = tfe.get_org_name_when_exists(organization=module.params['organization'])
    workspace = module.params['workspace']
    include = module.params['include']
    filter = module.params['filter']

    # Parse `runs` parameter and create list of runs.
    # It's possible someone passed a comma separated string, so we should handle that.
    # This can be either an empty list or '*' which means all runs.
    runs = []
    runs = [p.strip() for p in module.params['run']]
    runs = tfe.listify_comma_sep_strings_in_list(runs)
    if not runs:
        runs = [ '*' ]

    # Seed the result dict in the object
    result = dict(
        changed=False,
        organization=organization,
        workspace=workspace,
        runs=runs,
        filter=filter,
        include=include,
        json=dict(data=[], included=[]),
    )

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

    # To properly filter out run data, we need to collect all related resource
    if filter is not None:
        include = ['plan', 'apply', 'created_by', 'cost_estimate', 'configuration_version', 'configuration_version.ingress_attributes']

    # Process all runs
    if '*' in runs:

        # Retrieve information for all runs in the workspace
        try:        
            result_json = tfe.call_endpoint(tfe.api.runs.list_all, workspace_id=workspace_id, include=include)                  
        except Exception as e:
            module.fail_json(msg='Unable to list runs in "%s" workspace. Error: %s.' % (workspace, to_native(e)) )

        # Restrict results when as specified by filter. Otherwise, output the complte result set
        if filter is not None:
            result['json'] = restrict_results(filter=filter, result_input=result_json)
        else:
            result['json'] = result_json


    # Process the given runs
    else:
        # First, get the list of all runs without additional details
        try:        
            all_runs = tfe.call_endpoint(tfe.api.runs.list_all, workspace_id=workspace_id, include=None)
        except Exception as e:
            module.fail_json(msg='Unable to list runs in "%s" workspace. Error: %s.' % (workspace, to_native(e)) )

        result_json = dict( data=[], included=[] )

        # Next, iterate over the supplied runs to retrieve their details
        for run in runs:

            # Refer to a run by its custom message
            if any(r['attributes']['message'] == run for r in all_runs['data']):
                for selected_run in [r for r in all_runs['data'] if r['attributes']['message'] == run]:
                    try:        
                        ret = tfe.call_endpoint(tfe.api.runs.show, run_id=selected_run['id'], include=include)
                    except Exception as e:
                        module.fail_json(msg='Unable to retrieve details on a run in "%s" workspace. Error: %s.' % (workspace, to_native(e)) )

                    result_json['data'].append(ret['data'])
                    if include is not None:
                        result_json['included'].extend(ret['included']) 

            # Refer to a run by its ID
            else:
                try:        
                    ret = tfe.call_endpoint(tfe.api.runs.show, run_id=run, include=include)
                except Exception as e:
                    module.fail_json(msg='Unable to retrieve details on a run in "%s" workspace. Error: %s.' % (workspace, to_native(e)) )
      
                result_json['data'].append(ret['data'])
                if include is not None:
                    result_json['included'].extend(ret['included'])   

    # Restrict results when as specified by filter. Otherwise, output the complte result set
    if filter is not None:
        result['json'] = restrict_results(filter=filter, result_input=result_json)
    else:
        result['json'] = result_json

    # Remove duplicates from list of runs and list of nested resources
    if PY2:
        result['json']['data'] = {v['id']:v for v in result['json']['data']}.values()
        result['json']['included'] = {v['id']:v for v in result['json']['included']}.values()
    else:
        result['json']['data'] = list({v['id']:v for v in result['json']['data']}.values())
        result['json']['included'] = list({v['id']:v for v in result['json']['included']}.values())

    module.exit_json(**result)


if __name__ == '__main__':
    main()