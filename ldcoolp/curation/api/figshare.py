from figshare.figshare import issue_request

# Read in default configuration file
from ...config import config_default_dict

import pandas as pd
import numpy as np

from ldcoolp.logger import log_stdout


class FigshareInstituteAdmin:
    """
    Purpose:
      A Python interface for administration of institutional Figshare accounts

    :param figshare_dict: Dict that contains Figshare configuration.
      This should include:
        - api_token
        - stage bool

      Default: config_default_dict from config/default.ini

    Attributes
    ----------
    dict : dict
      Figshare configuration dictionary

    baseurl : str
      Base URL of the Figshare v2 API

    baseurl_institute : str
      Base URL of the Figshare v2 API for private institutions

    token : str
      The Figshare OAuth2 authentication token

    stage : bool
      Set to use API endpoint of stage instead of production
      Default: False (i.e., use production)

    headers : dict
      HTTP header information

    Methods
    -------
    endpoint(link)
      Concatenate the endpoint to the baseurl

    get_articles()
      Return pandas DataFrame of institutional articles
      See: https://docs.figshare.com/#private_institution_articles

    get_user_articles(account_id)
      Impersonate a user to retrieve articles associated with the user
      See: https://docs.figshare.com/#private_articles_list

    get_user_projects(account_id)
      Impersonate a user to retrieve projects associated with the user
      See: https://docs.figshare.com/#private_projects_list

    get_user_collections(account_id)
      Impersonate a user to retrieve collections associated with the user
      See: https://docs.figshare.com/#private_collections_list

    get_groups()
      Return pandas DataFrame of an institution's groups
      See: https://docs.figshare.com/#private_institution_groups_list

    get_account_list()
      Return pandas DataFrame of user accounts
      See: https://docs.figshare.com/#private_institution_accounts_list

    get_account_group_roles(account_id)
      Return dict containing group roles for a given account
      See: https://docs.figshare.com/#private_institution_account_group_roles

    get_account_details()
      Return pandas DataFrame that contains user information and their
      institutional and group roles

    get_curation_list()
      Return pandas DataFrame of datasets under curatorial review
      See: https://docs.figshare.com/#account_institution_curations

    get_curation_details(curation_id)
      Return dict containing curatorial details of a dataset

    get_curation_comments(curation_id)
      Return list containing curatorial comments of a dataset
      See: https://docs.figshare.com/#account_institution_curation_comments

    doi_check(article_id)
      Check if DOI is present/reserved

    reserve_doi(article_id)
      Reserve a DOI if one has not been reserved
      See: https://docs.figshare.com/#private_article_reserve_doi
    """

    def __init__(self, figshare_dict=config_default_dict['figshare'], log=None):
        self.dict = figshare_dict
        if not self.dict['stage']:
            self.baseurl = "https://api.figshare.com/v2/account/"
        else:
            self.baseurl = "https://api.figsh.com/v2/account/"

        self.baseurl_institute = self.baseurl + "institution/"
        self.token = self.dict['api_token']

        self.headers = {'Content-Type': 'application/json'}
        if self.token:
            self.headers['Authorization'] = f'token {self.token}'

        if isinstance(log, type(None)):
            self.log = log_stdout()
        else:
            self.log = log

    def endpoint(self, link, institute=True):
        """Concatenate the endpoint to the baseurl"""
        if institute:
            return self.baseurl_institute + link
        else:
            return self.baseurl + link

    def get_articles(self):
        """Retrieve information about articles within institutional instance"""
        url = self.endpoint("articles")

        # Figshare API is limited to a maximum of 1000 per page
        params = {'page': 1, 'page_size': 1000}
        articles = issue_request('GET', url, self.headers, params=params)

        articles_df = pd.DataFrame(articles)
        return articles_df

    def get_user_articles(self, account_id):
        url = self.endpoint("articles", institute=False)

        # Figshare API is limited to a maximum of 1000 per page
        params = {'page': 1, 'page_size': 1000, 'impersonate': account_id}
        user_articles = issue_request('GET', url, self.headers, params=params)

        user_articles_df = pd.DataFrame(user_articles)
        return user_articles_df

    def get_user_projects(self, account_id):
        url = self.endpoint("projects", institute=False)

        # Figshare API is limited to a maximum of 1000 per page
        params = {'page': 1, 'page_size': 1000, 'impersonate': account_id}
        user_projects = issue_request('GET', url, self.headers, params=params)

        user_projects_df = pd.DataFrame(user_projects)
        return user_projects_df

    def get_user_collections(self, account_id):
        url = self.endpoint("collections", institute=False)

        # Figshare API is limited to a maximum of 1000 per page
        params = {'page': 1, 'page_size': 1000, 'impersonate': account_id}
        user_collections = issue_request('GET', url, self.headers, params=params)

        user_collections_df = pd.DataFrame(user_collections)
        return user_collections_df

    def get_groups(self):
        """Retrieve information about groups within institutional instance"""
        url = self.endpoint("groups")
        groups = issue_request('GET', url, self.headers)

        groups_df = pd.DataFrame(groups)
        return groups_df

    def get_account_list(self, ignore_admin=False):
        """Retrieve accounts within institutional instance"""
        url = self.endpoint("accounts")

        # Figshare API is limited to a maximum of 1000 per page
        params = {'page': 1, 'page_size': 1000}
        accounts = issue_request('GET', url, self.headers, params=params)

        accounts_df = pd.DataFrame(accounts)
        accounts_df = accounts_df.drop(columns='institution_id')

        if ignore_admin:
            self.log.info("Excluding administrative and test accounts")

            drop_index = list(accounts_df[accounts_df['email'] ==
                                          'data-management@email.arizona.edu'].index)
            drop_index += list(accounts_df[accounts_df['email'].str.contains('-test@email.arizona.edu')].index)

            accounts_df = accounts_df.drop(drop_index).reset_index(drop=True)
        return accounts_df

    def get_account_group_roles(self, account_id):
        """Retrieve group roles for a given account"""
        url = self.endpoint(f"roles/{account_id}")

        roles = issue_request('GET', url, self.headers)
        return roles

    def get_account_details(self, flag=True, ignore_admin=False):
        """
        Retrieve account details. This includes number of articles, projects,
        collections, group association, and administrative and reviewer flags
        """

        # Retrieve accounts
        accounts_df = self.get_account_list(ignore_admin=ignore_admin)

        n_accounts = accounts_df.shape[0]

        # Retrieve groups
        groups_df = self.get_groups()

        num_articles = np.zeros(n_accounts, dtype=np.int)
        num_projects = np.zeros(n_accounts, dtype=np.int)
        num_collections = np.zeros(n_accounts, dtype=np.int)

        if flag:
            admin_flag = [''] * n_accounts
            reviewer_flag = [''] * n_accounts
        group_assoc = ['N/A'] * n_accounts

        # Determine group roles for each account
        for n, account_id in zip(range(n_accounts), accounts_df['id']):
            roles = self.get_account_group_roles(account_id)

            try:
                articles_df = self.get_user_articles(account_id)
                num_articles[n] = articles_df.shape[0]
            except Exception:
                self.log.warn(f"Unable to retrieve articles for : {account_id}")

            try:
                projects_df = self.get_user_projects(account_id)
                num_projects[n] = projects_df.shape[0]
            except Exception:
                self.log.warn(f"Unable to retrieve projects for : {account_id}")

            try:
                collections_df = self.get_user_collections(account_id)
                num_collections[n] = collections_df.shape[0]
            except Exception:
                self.log.warn(f"Unable to retrieve collections for : {account_id}")

            for key in roles.keys():
                for t_dict in roles[key]:
                    if t_dict['id'] == 11:
                        group_assoc[n] = key
                    if flag:
                        if t_dict['id'] == 2:
                            admin_flag[n] = 'X'
                        if t_dict['id'] == 49:
                            reviewer_flag[n] = 'X'

        accounts_df['Articles'] = num_articles
        accounts_df['Projects'] = num_projects
        accounts_df['Collections'] = num_collections

        if flag:
            accounts_df['Admin'] = admin_flag
            accounts_df['Reviewer'] = reviewer_flag

        for group_id, group_name in zip(groups_df['id'], groups_df['name']):
            self.log.info(f"{group_id} - {group_name}")
            group_assoc = [sub.replace(str(group_id), group_name) for
                           sub in group_assoc]

        accounts_df['Group'] = group_assoc

        return accounts_df

    def get_curation_list(self, article_id=None):
        """Retrieve list of curation"""

        url = self.endpoint("reviews")

        params = {'offset': 0, 'limit': 1000}
        if not isinstance(article_id, type(None)):
            params['article_id'] = article_id

        curation_list = issue_request('GET', url, self.headers, params=params)

        curation_df = pd.DataFrame(curation_list)
        return curation_df

    def get_curation_details(self, curation_id):
        """Retrieve details about a specified curation item"""

        url = self.endpoint(f"review/{curation_id}")

        curation_details = issue_request('GET', url, self.headers)

        return curation_details

    def get_curation_comments(self, curation_id):
        """Retrieve comments about specified curation item"""

        url = self.endpoint(f"review/{curation_id}/comments")

        curation_comments = issue_request('GET', url, self.headers)

        return curation_comments

    def doi_check(self, article_id):
        """Check if DOI is present/reserved"""
        url = self.endpoint(f"articles/{article_id}", institute=False)

        article_details = issue_request('GET', url, self.headers)

        check = False
        if article_details['doi']:
            check = True

        return check, article_details['doi']

    def reserve_doi(self, article_id):
        """Reserve DOI if one has not been reserved"""

        url = self.endpoint(f"articles/{article_id}/reserve_doi", institute=False)

        # Check if DOI has been reserved
        doi_check, doi_string = self.doi_check(article_id)

        if doi_check:
            self.log.info("DOI already reserved! Skipping... ")

            return doi_string
        else:
            self.log.info("PROMPT: DOI reservation has not occurred! Do you wish to reserve?")
            src_input = input("PROMPT: Type 'Yes'/'yes'. Anything else will skip : ")
            self.log.info(f"RESPONSE: {src_input}")
            if src_input.lower() == 'yes':
                self.log.info("Reserving DOI ... ")
                response = issue_request('POST', url, self.headers)
                self.log.info(f"DOI minted : {response['doi']}")
                return response['doi']
            else:
                self.log.warn("Skipping... ")
                return doi_string
