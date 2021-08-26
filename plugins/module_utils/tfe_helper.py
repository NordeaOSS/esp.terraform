# -*- coding: utf-8 -*-

# Author: Krzysztof Lewandowski <Krzysztof.Lewandowski@nordea.com>

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import os
import time
from terrasnek.api import TFC

from ansible.module_utils.basic import env_fallback
from ansible.module_utils.common.text.converters import to_bytes, to_native, to_text

#
# class: TFEHelper
#

class TFEHelper:
    TFE_URL = 'https://terraform.example.com'


    def __init__(self, module):
        self.module = module
        if self.module.params['url'] is None:
            self.module.params['url'] = self.TFE_URL

        self.api = TFC(self.module.params['token'], url=self.module.params['url'], verify=self.module.params['validate_certs'])


    @staticmethod
    def tfe_argument_spec():
        return dict(
            url=dict(type='str', no_log=False, required=False, fallback=(env_fallback, ['TFE_URL'])),
            token=dict(type='str', no_log=True, required=False, default=None,
                       fallback=(env_fallback, ['TFE_TOKEN'])),
            validate_certs=dict(type='bool', default=True, fallback=(env_fallback, ['SSL_VERIFY'])),
            use_proxy=dict(type='bool', default=True),
            sleep=dict(type='int', default=5),
            retries=dict(type='int', default=3),
        )


    def call_endpoint(self, endpoint=None, **kwargs):
        """
        Call TFE endpoint with parameters provided in arguments

        It will try to call the endpoint 'retries' times until it gives up.
        """  
        exception = None
        retries = 1
        while retries <= self.module.params['retries']:
            try:
                ret = endpoint(**kwargs)
                return ret   
            except Exception as e:                
                exception = e
                time.sleep(self.module.params['sleep'])
                retries += 1

        # Chain exceptions
        raise exception

        return None


    def listify_comma_sep_strings_in_list(self, some_list):
        """
        method to accept a list of strings as the parameter, find any strings
        in that list that are comma separated, remove them from the list and add
        their comma separated elements to the original list
        """
        new_list = []
        remove_from_original_list = []
        for element in some_list:
            if ',' in element:
                remove_from_original_list.append(element)
                new_list.extend([e.strip() for e in element.split(',')])

        for element in remove_from_original_list:
            some_list.remove(element)

        some_list.extend(new_list)

        if some_list == [""]:
            return []

        return some_list


    def get_org_name_when_exists(self, organization=None, return_org_name_on_unauthorized=True):
        """
            Searches for existing organization (by its name/id and/or its external-id).
            Returns the organization name, when it exists. Otherwise, it returns None.

            'organization' parameter may represent the organization id/noame or external-id
        """
        # First, get the list of all organizations
        try:        
            all_organizations = self.call_endpoint(self.api.orgs.list)
        except Exception as e:
            if return_org_name_on_unauthorized:
                return organization
            else:
                self.module.fail_json(msg='Unable to list organizations. Error: %s.' % (to_native(e)) )

        org_name = None

        # Try to find organization by its external-id
        if any(o['attributes']['external-id'] == organization for o in all_organizations['data']):
            org_name = [o for o in all_organizations['data'] if o['attributes']['external-id'] == organization][0]['id']       

        if (org_name is None) and any(o['id'] == organization for o in all_organizations['data']):
            # Next, try to find organization by its name
            org_name = [o for o in all_organizations['data'] if o['id'] == organization][0]['id'] 

        return org_name


    def is_subset(self, subset=None, superset=None):
        """
        Check if 'subset' is subset of 'superset'

        """
        if isinstance(subset, dict):
            return all(key in superset and self.is_subset(val, superset[key]) for key, val in subset.items())

        if isinstance(subset, list) or isinstance(subset, set):
            return all(any(self.is_subset(subitem, superitem) for superitem in superset) for subitem in subset)

        # assume that subset is a plain value if none of the above match
        return subset == superset
