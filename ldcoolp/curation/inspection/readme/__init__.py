from os.path import exists, join, dirname
from os import walk

# Template engine
from jinja2 import Environment, FileSystemLoader
from html2text import html2text

from ....admin import permissions
from . import populate

import configparser

# Read in default configuration file
from ldcoolp import config_file
config = configparser.ConfigParser()
config.read(config_file)

folder_copy_data = config.get('curation', 'folder_copy_data')
folder_data = config.get('curation', 'folder_data')

source = config.get('curation', 'source')
root_directory = config.get('curation', '{}_path'.format(source))

underreview_folder = config.get('curation', 'folder_underreview')

root_directory = join(root_directory, underreview_folder)

readme_template = config.get('curation', 'readme_template')


class ReadmeClass:
    """
    Purpose:
      A ReadmeClass object for retrieval and population of README.txt
      files.  It uses existing metadata information from Figshare to
      populate common information that are provided

    Attributes
    ----------
    dn : DepositorName object
      Contains information about the depositor and author(s)

    folderName : str
      Folder name identifying depositor and corresponding author

    article_id : int
      Figshare article ID

    article_dict : dict
      dictionary containing curation details

    data_path : str
      Path DATA folder (this is the working copy and not the ORIGINAL_DATA)

    readme_file_path : str
      Full filename for exported README.txt

    readme_template: jinja2.environment.Template

    readme_dict : dict
      Dictionary containing metadata information to provide to jinja template

    Methods
    -------
    import_template(template)
      Returns a jinja2 template by importing markdown README file (README_template.txt) into jinja template

    retrieve article_metadata()
      Returns a dictionary containing metadata for jinja2 template

    construct()
      Write README.txt by using jinja2 rendering

    retrieve()
      Checks to see if file exists and execute construct()

    walkthrough(data_path, ignore)
      Identify other possible locations for README.txt

    main()
      Construct README.txt by calling retrieve
    """

    def __init__(self, dn):
        self.dn = dn
        self.folderName = self.dn.folderName
        self.article_id = self.dn.article_id
        self.article_dict = self.dn.curation_dict

        self.data_path = join(root_directory, self.folderName,
                              folder_copy_data)

        # This is the path of the final README.txt file for creation
        self.readme_file_path = join(self.data_path, 'README.txt')

        # Use README template in DATA folder if exists. Otherwise, use default
        user_readme_template = join(self.data_path, readme_template)
        if exists(user_readme_template):
            print(f"{readme_template} found in DATA folder!")
            src_input = input("Type 'Yes' if you wish to use.  Anything else will use 'default' : ")
            if src_input == 'Yes':
                self.template_source = 'user'
            else:
                self.template_source = 'default'
        else:
            print("Unable to find README_template.txt in DATA folder. Using 'default'")
            self.template_source = 'default'

        self.readme_template = self.import_template(temp_src=self.template_source)

        self.readme_dict = self.retrieve_article_metadata()

    def import_template(self, temp_src='default'):
        if temp_src not in ['default', 'user']:
            print("Incorrect [template] input")
            raise ValueError

        template_location = dirname(__file__)
        if temp_src == 'user':
            template_location = self.data_path

        file_loader = FileSystemLoader(template_location)
        env = Environment(loader=file_loader)

        jinja_template = env.get_template(readme_template)
        return jinja_template

    def retrieve_article_metadata(self):
        """
        Purpose:
          Retrieve metadata from figshare API to strip out information to
          populate in README.txt file for basic content

        :return readme_dict: dict containing essential metadata for README.txt
        """

        readme_dict = dict()

        # Retrieve title of deposit
        readme_dict['title'] = self.article_dict['item']['title']

        # Retrieve preferred citation. Default: ReDATA in DataCite format
        # This forces a period after the year and ensures multiple rows
        # with the last two row merged for simplicity
        single_str_citation = self.article_dict['item']['citation']
        str_list = [str_row + '.' for str_row in
                    single_str_citation.replace('):', ').').split('. ')]
        citation_list = [content for content in str_list[0:-2]]
        citation_list.append(f"{str_list[-2]} {str_list[-1]}")
        readme_dict['preferred_citation'] = citation_list

        # If DOI available, retrieve:
        if 'doi' in self.article_dict['item']:
            readme_dict['doi'] = self.article_dict['item']['doi']
        else:
            readme_dict['doi'] = "10.25422/azu.data.[DOI_NUMBER]"

        readme_dict['lastname'] = self.dn.name_dict['surName']
        readme_dict['firstname'] = self.dn.name_dict['firstName']
        readme_dict['email'] = self.dn.name_dict['depositor_email']

        # Retrieve license
        readme_dict['license'] = self.article_dict['item']['license']['name']

        # Retrieve author
        readme_dict['first_author'] = \
            self.article_dict['item']['authors'][0]['full_name']

        # Retrieve description (single string)
        readme_dict['description'] = html2text(self.article_dict['item']['description'])

        # Retrieve references as list
        readme_dict['references'] = self.article_dict['item']['references']

        return readme_dict

    def construct(self):
        """
        Purpose:
          Create README.txt file with jinja2 README template and populate with
          metadata information

        """

        if not exists(self.readme_file_path):
            print(f"Constructing README file based on {self.template_source} template...")

            # Write file
            print(f"Writing file : {self.readme_file_path}")
            f = open(self.readme_file_path, 'w')

            content_list = self.readme_template.render(readme_dict=self.readme_dict)
            f.writelines(content_list)
            f.close()
        else:
            print("Default README file found! Not overwriting with template!")

        # Set permission for rwx
        permissions.curation(self.readme_file_path)

    @staticmethod
    def walkthrough(data_path, ignore=''):
        """
        Purpose:
          Perform walkthrough to find other README files

        :param data_path: path to DATA folder
        :param ignore: full path of default README.txt to ignore
        :return:
        """

        for dir_path, dir_names, files in walk(data_path):
            for file in files:
                if 'README' in file.upper():  # case insensitive
                    file_fullname = join(dir_path, file)
                    if file_fullname != ignore:
                        print("File exists : {}".format(file_fullname))

    def main(self):
        """
        Purpose:
          Check that a README file exists

        :return: Will raise error
        """

        if exists(self.readme_file_path):
            print("Default README.txt file exists!!!")

            print("Checking for additional README files")
            self.walkthrough(self.data_path, ignore=self.readme_file_path)
        else:
            print("Default README.txt file DOES NOT exist!!!")
            print("Searching other possible locations...")

            self.walkthrough(self.data_path)

            user_response = input("If you wish to create a README file, type 'Yes'. RETURN KEY will exit : ")
            if user_response == "Yes":
                self.construct()
            else:
                print("Exiting script")
                return
