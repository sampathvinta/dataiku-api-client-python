from ..utils import DataikuException
from ..utils import DataikuUTF8CSVReader
from ..utils import DataikuStreamedHttpUTF8CSVReader
from .future import DSSFuture
import json, warnings
from .utils import DSSTaggableObjectListItem
from .future import DSSFuture
from .metrics import ComputedMetrics
from .discussion import DSSObjectDiscussions
from .statistics import DSSStatisticsWorksheet
from . import recipe

class DSSDatasetListItem(DSSTaggableObjectListItem):
    """An item in a list of datasets. Do not instantiate this class"""
    def __init__(self, client, data):
        super(DSSDatasetListItem, self).__init__(data)
        self.client = client

    def to_dataset(self):
        """Gets the :class:`DSSDataset` corresponding to this dataset"""
        return DSSDataset(self.client, self._data["projectKey"], self._data["name"])

    @property
    def name(self):
        return self._data["name"]
    @property
    def id(self):
        return self._data["name"]
    @property
    def type(self):
        return self._data["type"]
    @property
    def schema(self):
        return self._data["schema"]

    @property
    def connection(self):
        """Returns the connection on which this dataset is attached, or None if there is no connection for this dataset"""
        if not "params" in self._data:
            return None
        return self._data["params"].get("connection", None)

    def get_column(self, column):
        """
        Returns the schema column given a name.
        :param str column: Column to find
        :return a dict of the column settings or None if column does not exist
        """
        matched = [col for col in self.schema["columns"] if col["name"] == column]
        return None if len(matched) == 0 else matched[0]

class DSSDataset(object):
    """
    A dataset on the DSS instance
    """
    def __init__(self, client, project_key, dataset_name):
        self.client = client
        self.project = client.get_project(project_key)
        self.project_key = project_key
        self.dataset_name = dataset_name

    ########################################################
    # Dataset deletion
    ########################################################

    def delete(self, drop_data=False):
        """
        Delete the dataset

        :param bool drop_data: Should the data of the dataset be dropped
        """
        return self.client._perform_empty(
            "DELETE", "/projects/%s/datasets/%s" % (self.project_key, self.dataset_name), params = {
                "dropData" : drop_data
            })


    ########################################################
    # Dataset definition
    ########################################################

    def get_settings(self):
        """
        Returns the settings of this dataset as a :class:`DSSDatasetSettings`, or one of its subclasses.

        Know subclasses of :class:`DSSDatasetSettings` include :class:`FSLikeDatasetSettings` 
        and :class:`SQLDatasetSettings`

        You must use :meth:`~DSSDatasetSettings.save()` on the returned object to make your changes effective
        on the dataset.

        .. code-block:: python

            # Example: activating discrete partitioning on a SQL dataset
            dataset = project.get_dataset("my_database_table")
            settings = dataset.get_settings()
            settings.add_discrete_partitioning_dimension("country")
            settings.save()

        :rtype: :class:`DSSDatasetSettings`
        """
        data = self.client._perform_json("GET", "/projects/%s/datasets/%s" % (self.project_key, self.dataset_name))

        if data["type"] in self.__class__.FS_TYPES:
            return FSLikeDatasetSettings(self, data)
        elif data["type"] in self.__class__.SQL_TYPES:
            return SQLDatasetSettings(self, data)
        else:
            return DSSDatasetSettings(self, data)


    def get_definition(self):
        """
        Deprecated. Use :meth:`get_settings`
        Get the raw settings of the dataset as a dict
        :rtype: dict
        """
        warnings.warn("Dataset.get_definition is deprecated, please use get_settings", DeprecationWarning)
        return self.client._perform_json(
                "GET", "/projects/%s/datasets/%s" % (self.project_key, self.dataset_name))

    def set_definition(self, definition):
        """
        Deprecated. Use :meth:`get_settings` and :meth:`DSSDatasetSettings.save`
        Set the definition of the dataset
        
        :param definition: the definition, as a dict. You should only set a definition object 
                            that has been retrieved using the get_definition call.
        """
        warnings.warn("Dataset.set_definition is deprecated, please use get_settings", DeprecationWarning)
        return self.client._perform_json(
                "PUT", "/projects/%s/datasets/%s" % (self.project_key, self.dataset_name),
                body=definition)

    ########################################################
    # Dataset metadata
    ########################################################

    def get_schema(self):
        """
        Get the schema of the dataset
        
        Returns:
            a JSON object of the schema, with the list of columns
        """
        return self.client._perform_json(
                "GET", "/projects/%s/datasets/%s/schema" % (self.project_key, self.dataset_name))

    def set_schema(self, schema):
        """
        Set the schema of the dataset
        
        Args:
            schema: the desired schema for the dataset, as a JSON object. All columns have to provide their
            name and type
        """
        return self.client._perform_json(
                "PUT", "/projects/%s/datasets/%s/schema" % (self.project_key, self.dataset_name),
                body=schema)

    def get_metadata(self):
        """
        Get the metadata attached to this dataset. The metadata contains label, description
        checklists, tags and custom metadata of the dataset
        
        Returns:
            a dict object. For more information on available metadata, please see
            https://doc.dataiku.com/dss/api/5.0/rest/
        """
        return self.client._perform_json(
                "GET", "/projects/%s/datasets/%s/metadata" % (self.project_key, self.dataset_name))

    def set_metadata(self, metadata):
        """
        Set the metadata on this dataset.
        
        Args:
            metadata: the new state of the metadata for the dataset. You should only set a metadata object 
            that has been retrieved using the get_metadata call.
        """
        return self.client._perform_json(
                "PUT", "/projects/%s/datasets/%s/metadata" % (self.project_key, self.dataset_name),
                body=metadata)


    ########################################################
    # Dataset data
    ########################################################

    def iter_rows(self, partitions=None):
        """
        Get the dataset's data
        
        Return:
            an iterator over the rows, each row being a tuple of values. The order of values
            in the tuples is the same as the order of columns in the schema returned by get_schema
        """
        csv_stream = self.client._perform_raw(
                "GET" , "/projects/%s/datasets/%s/data/" %(self.project_key, self.dataset_name),
                params = {
                    "format" : "tsv-excel-noheader",
                    "partitions" : partitions
                })

        return DataikuStreamedHttpUTF8CSVReader(self.get_schema()["columns"], csv_stream).iter_rows()


    def list_partitions(self):
        """
        Get the list of all partitions of this dataset
        
        Returns:
            the list of partitions, as a list of strings
        """
        return self.client._perform_json(
                "GET", "/projects/%s/datasets/%s/partitions" % (self.project_key, self.dataset_name))


    def clear(self, partitions=None):
        """
        Clear all data in this dataset
        
        Args:
            partitions: (optional) a list of partitions to clear. When not provided, the entire dataset
            is cleared
        """
        return self.client._perform_json(
                "DELETE", "/projects/%s/datasets/%s/data" % (self.project_key, self.dataset_name),
                params={"partitions" : partitions})

    def copy_to(self, target, sync_schema=True, write_mode="OVERWRITE"):
        """
        Copies the data of this dataset to another dataset

        :param target Dataset: a :class:`dataikuapi.dss.dataset.DSSDataset` representing the target of this copy
        :returns: a DSSFuture representing the operation
        """
        dqr = {
             "targetProjectKey" : target.project_key,
             "targetDatasetName": target.dataset_name,
             "syncSchema": sync_schema,
             "writeMode" : write_mode
        }
        future_resp = self.client._perform_json("POST", "/projects/%s/datasets/%s/actions/copyTo" % (self.project_key, self.dataset_name), body=dqr)
        return DSSFuture(self.client, future_resp.get("jobId", None), future_resp)

    ########################################################
    # Dataset actions
    ########################################################

    def build(self, job_type="NON_RECURSIVE_FORCED_BUILD", partitions=None, wait=True, no_fail=False):
        """
        Starts a new job to build this dataset and wait for it to complete.
        Raises if the job failed.

        .. code-block:: python

            job = dataset.build()
            print("Job %s done" % job.id)

        :param job_type: The job type. One of RECURSIVE_BUILD, NON_RECURSIVE_FORCED_BUILD or RECURSIVE_FORCED_BUILD
        :param partitions: If the dataset is partitioned, a list of partition ids to build
        :param no_fail: if True, does not raise if the job failed.
        :return: the :class:`dataikuapi.dss.job.DSSJob` job handle corresponding to the built job
        :rtype: :class:`dataikuapi.dss.job.DSSJob`
        """
        jd = self.project.new_job(job_type)
        jd.with_output(self.dataset_name, partition=partitions)
        if wait:
            return jd.start_and_wait()
        else:
            return jd.start()


    def synchronize_hive_metastore(self):
        """
        Synchronize this dataset with the Hive metastore
        """
        self.client._perform_empty(
                "POST" , "/projects/%s/datasets/%s/actions/synchronizeHiveMetastore" %(self.project_key, self.dataset_name))

    def update_from_hive(self):
        """
        Resynchronize this dataset from its Hive definition
        """
        self.client._perform_empty(
                "POST", "/projects/%s/datasets/%s/actions/updateFromHive" %(self.project_key, self.dataset_name))

    def compute_metrics(self, partition='', metric_ids=None, probes=None):
        """
        Compute metrics on a partition of this dataset.
        If neither metric ids nor custom probes set are specified, the metrics
        setup on the dataset are used.
        """
        url = "/projects/%s/datasets/%s/actions" % (self.project_key, self.dataset_name)
        if metric_ids is not None:
            return self.client._perform_json(
                    "POST" , "%s/computeMetricsFromIds" % url,
                    params={'partition':partition}, body={"metricIds" : metric_ids})
        elif probes is not None:
            return self.client._perform_json(
                    "POST" , "%s/computeMetrics" % url,
                    params={'partition':partition}, body=probes)
        else:
            return self.client._perform_json(
                    "POST" , "%s/computeMetrics" % url,
                    params={'partition':partition})

    def run_checks(self, partition='', checks=None):
        """
        Run checks on a partition of this dataset. If the checks are not specified, the checks
        setup on the dataset are used.
        """
        if checks is None:
            return self.client._perform_json(
                    "POST" , "/projects/%s/datasets/%s/actions/runChecks" %(self.project_key, self.dataset_name),
                    params={'partition':partition})
        else:
            return self.client._perform_json(
                    "POST" , "/projects/%s/datasets/%s/actions/runChecks" %(self.project_key, self.dataset_name),
                    params={'partition':partition}, body=checks)

    def uploaded_add_file(self, fp, filename):
        """
        Adds a file to an "uploaded files" dataset

        :param file fp: A file-like object that represents the file to upload
        :param str filename: The filename for the file to upload 
        """
        self.client._perform_empty("POST", "/projects/%s/datasets/%s/uploaded/files" % (self.project_key, self.dataset_name),
         files={"file":(filename, fp)})

    def uploaded_list_files(self):
        """
        List the files in an "uploaded files" dataset
        """
        return self.client._perform_json("GET", "/projects/%s/datasets/%s/uploaded/files" % (self.project_key, self.dataset_name))


    ########################################################
    # Statistics worksheets
    ########################################################

    def list_statistics_worksheets(self, as_objects=True):
        """
        List the statistics worksheets associated to this dataset.

        :rtype: list of :class:`dataikuapi.dss.statistics.DSSStatisticsWorksheet`
        """
        worksheets = self.client._perform_json(
            "GET", "/projects/%s/datasets/%s/statistics/worksheets/" % (self.project_key, self.dataset_name))
        if as_objects:
            return [self.get_statistics_worksheet(worksheet['id']) for worksheet in worksheets]
        else:
            return worksheets

    def create_statistics_worksheet(self, name="My worksheet"):
        """
        Create a new worksheet in the dataset, and return a handle to interact with it.

        :param string input_dataset: input dataset of the worksheet
        :param string worksheet_name: name of the worksheet

        Returns:
            A :class:`dataikuapi.dss.statistics.DSSStatisticsWorksheet` dataset handle
        """

        worksheet_definition = {
            "projectKey": self.project_key,
            "name": name,
            "dataSpec": {
                "inputDatasetSmartName": self.dataset_name,
                "datasetSelection": {
                    "partitionSelectionMethod": "ALL",
                    "maxRecords": 30000,
                    "samplingMethod": "FULL"
                }
            }
        }
        created_worksheet = self.client._perform_json(
            "POST", "/projects/%s/datasets/%s/statistics/worksheets/" % (self.project_key, self.dataset_name),
            body=worksheet_definition
        )
        return self.get_statistics_worksheet(created_worksheet['id'])

    def get_statistics_worksheet(self, worksheet_id):
        """
        Get a handle to interact with a statistics worksheet

        :param string worksheet_id: the ID of the desired worksheet

        :returns: A :class:`dataikuapi.dss.statistics.DSSStatisticsWorksheet` worksheet handle
        """
        return DSSStatisticsWorksheet(self.client, self.project_key, self.dataset_name, worksheet_id)

    ########################################################
    # Metrics
    ########################################################

    def get_last_metric_values(self, partition=''):
        """
        Get the last values of the metrics on this dataset

        Returns:
            a list of metric objects and their value
        """
        return ComputedMetrics(self.client._perform_json(
                "GET", "/projects/%s/datasets/%s/metrics/last/%s" % (self.project_key, self.dataset_name, 'NP' if len(partition) == 0 else partition)))


    def get_metric_history(self, metric, partition=''):
        """
        Get the history of the values of the metric on this dataset

        Returns:
            an object containing the values of the metric, cast to the appropriate type (double, boolean,...)
        """
        return self.client._perform_json(
                "GET", "/projects/%s/datasets/%s/metrics/history/%s" % (self.project_key, self.dataset_name, 'NP' if len(partition) == 0 else partition),
                params={'metricLookup' : metric if isinstance(metric, str) or isinstance(metric, unicode) else json.dumps(metric)})

    ########################################################
    # Usages
    ########################################################

    def get_usages(self):
        """
        Get the recipes or analyses referencing this dataset

        Returns:
            a list of usages
        """
        return self.client._perform_json("GET", "/projects/%s/datasets/%s/usages" % (self.project_key, self.dataset_name))

    ########################################################
    # Discussions
    ########################################################
    def get_object_discussions(self):
        """
        Get a handle to manage discussions on the dataset

        :returns: the handle to manage discussions
        :rtype: :class:`dataikuapi.discussion.DSSObjectDiscussions`
        """
        return DSSObjectDiscussions(self.client, self.project_key, "DATASET", self.dataset_name)

    ########################################################
    # Test / Autofill
    ########################################################

    FS_TYPES = ["Filesystem", "UploadedFiles", "FilesInFolder",
                "HDFS", "S3", "Azure", "GCS", "FTP", "SCP", "SFTP"]
    # HTTP is FSLike but not FS                

    SQL_TYPES = ["JDBC", "PostgreSQL", "MySQL", "Vertica", "Snowflake", "Redshift",
                "Greenplum", "Teradata", "Oracle", "SQLServer", "SAPHANA", "Netezza",
                "BigQuery", "Athena", "hiveserver2"]

    def test_and_detect(self, infer_storage_types=False):
        settings = self.get_settings()

        if settings.get_type() in self.__class__.FS_TYPES:
            future_resp = self.client._perform_json("POST",
                "/projects/%s/datasets/%s/actions/testAndDetectSettings/fsLike"% (self.project_key, self.dataset_name),
                body = {"detectPossibleFormats" : True, "inferStorageTypes" : infer_storage_types })

            return DSSFuture(self.client, future_resp.get('jobId', None), future_resp)
        elif settings.get_type() in self.__class__.SQL_TYPES:
            return self.client._perform_json("POST",
                "/projects/%s/datasets/%s/actions/testAndDetectSettings/externalSQL"% (self.project_key, self.dataset_name))
        else:
            raise ValueError("don't know how to test/detect on dataset type:%s" % settings.get_type())

    def autodetect_settings(self, infer_storage_types=False):
        settings = self.get_settings()

        if settings.get_type() in self.__class__.FS_TYPES:
            future = self.test_and_detect(infer_storage_types)
            result = future.wait_for_result()

            if not "format" in result or not result["format"]["ok"]:
                raise DataikuException("Format detection failed, complete response is " + json.dumps(result))

            settings.get_raw()["formatType"] = result["format"]["type"]
            settings.get_raw()["formatParams"] = result["format"]["params"]
            settings.get_raw()["schema"] = result["format"]["schemaDetection"]["newSchema"]

            return settings

        elif settings.get_type() in self.__class__.SQL_TYPES:
            result = self.test_and_detect()

            if not "schemaDetection" in result:
                raise DataikuException("Format detection failed, complete response is " + json.dumps(result))

            settings.get_raw()["schema"] = result["schemaDetection"]["newSchema"]
            return settings

        else:
            raise ValueError("don't know how to test/detect on dataset type:%s" % settings.get_type())

    def get_as_core_dataset(self):
        import dataiku
        return dataiku.Dataset("%s.%s" % (self.project_key, self.dataset_name))

    ########################################################
    # Creation of recipes
    ########################################################

    def new_code_recipe(self, type, code=None, recipe_name=None):
        """Starts creation of a new code recipe taking this dataset as input"""

        if recipe_name is None:
            recipe_name = "%s_recipe_from_%s" % (type, self.dataset_name)

        if type == "python":
            builder = recipe.PythonRecipeCreator(recipe_name, self.project)
        else:
            builder = recipe.CodeRecipeCreator(recipe_name, type, self.project)
        builder.with_input(self.dataset_name)
        if code is not None:
            builder.with_script(code)
        return builder

    def new_grouping_recipe(self, first_group_by, recipe_name=None):
        if recipe_name is None:
            recipe_name = "group_%s" % (self.dataset_name)
        builder = recipe.GroupingRecipeCreator(recipe_name, self.project)
        builder.with_input(self.dataset_name)
        builder.with_group_key(first_group_by)
        return builder

class DSSDatasetSettings(object):
    def __init__(self, dataset, settings):
        self.dataset = dataset
        self.settings = settings

    def get_raw(self):
        """Get the raw dataset settings as a dict"""
        return self.settings

    def get_raw_params(self):
        """Get the type-specific params, as a raw dict"""
        return self.settings["params"]

    def get_type(self):
        return self.settings["type"]

    def remove_partitioning(self):
        self.settings["partitioning"] = {"dimensions" : []}

    def add_discrete_partitioning_dimension(self, dim_name):
        self.settings["partitioning"]["dimensions"].append({"name": dim_name, "type": "value"})

    def add_time_partitioning_dimension(self, dim_name, period="DAY"):
        self.settings["partitioning"]["dimensions"].append({"name": dim_name, "type": "time", "params":{"period": period}})

    def add_raw_schema_column(self, column):
        self.settings["schema"]["columns"].append(column)

    def save(self):
        self.dataset.client._perform_empty(
                "PUT", "/projects/%s/datasets/%s" % (self.dataset.project_key, self.dataset.dataset_name),
                body=self.settings)

class FSLikeDatasetSettings(DSSDatasetSettings):
    def __init__(self, dataset, settings):
        super(FSLikeDatasetSettings, self).__init__(dataset, settings)

    def set_connection_and_path(self, connection, path):
        self.settings["params"]["connection"] = connection
        self.settings["params"]["path"] = path

    def get_raw_format_params(self):
        """Get the raw format parameters as a dict""" 
        return self.settings["formatParams"]

    def set_format(self, format_type, format_params = None):
        if format_params is None:
            format_params = {}
        self.settings["formatType"] = format_type
        self.settings["formatParams"] = format_params

    def set_csv_format(self, separator=",", style="excel", skip_rows_before=0, header_row=True, skip_rows_after=0):
        format_params = {
            "style" : style,
            "separator":  separator,
            "skipRowsBeforeHeader":  skip_rows_before,
            "parseHeaderRow":  header_row,
            "skipRowsAfterHeader":  skip_rows_after
        }
        self.set_format("csv", format_params)

    def set_partitioning_file_pattern(self, pattern):
        self.settings["partitioning"]["filePathPattern"] = pattern

class SQLDatasetSettings(DSSDatasetSettings):
    def __init__(self, dataset, settings):
        super(SQLDatasetSettings, self).__init__(dataset, settings)

    def set_table(self, connection, schema, table):
        """Sets this SQL dataset in 'table' mode, targeting a particular table of a connection"""
        self.settings["params"].update({
            "connection": connection,
            "mode": "table",
            "schema": schema,
            "table": table
        })

class DSSManagedDatasetCreationHelper(object):

    def __init__(self, project, dataset_name):
        self.project = project
        self.dataset_name = dataset_name
        self.creation_settings = { "specificSettings" : {} }

    def get_creation_settings(self):
        return self.creation_settings

    def with_store_into(self, connection, type_option_id = None, format_option_id = None):
        """
        Sets the connection into which to store the new managed dataset
        :param str connection: Name of the connection to store into
        :param str type_option_id: If the connection accepts several types of datasets, the type
        :param str format_option_id: Optional identifier of a file format option
        :return: self
        """
        self.creation_settings["connectionId"] = connection
        if type_option_id is not None:
            self.creation_settings["typeOptionId"] = type_option_id
        if format_option_id is not None:
            self.creation_settings["specificSettings"]["formatOptionId"] = format_option_id 
        return self

    def with_copy_partitioning_from(self, dataset_ref, object_type='DATASET'):
        """
        Sets the new managed dataset to use the same partitioning as an existing dataset_name

        :param str dataset_ref: Name of the dataset to copy partitioning from
        :return: self
        """
        code = 'dataset' if object_type == 'DATASET' else 'folder'
        self.creation_settings["partitioningOptionId"] = "copy:%s:%s" % (code, dataset_ref)
        return self

    def create(self):
        """
        Executes the creation of the managed dataset according to the selected options

        :return: The :class:`DSSDataset` corresponding to the newly created dataset
        """
        self.project.client._perform_json("POST", "/projects/%s/datasets/managed" % self.project.project_key,
            body = {
                "name": self.dataset_name,
                "creationSettings":  self.creation_settings
        })
        return DSSDataset(self.project.client, self.project.project_key, self.dataset_name)