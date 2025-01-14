from .future import FMFuture


class FMVirtualNetworkCreator(object):
    def __init__(self, client, label):
        """
        A builder class to create a Virtual Network

        :param str label: The label of the Virtual Network
        """
        self.client = client
        self.data = {}
        self.use_default_values = False
        self.data["label"] = label
        self.data["mode"] = "EXISTING_MONOTENANT"

    def with_internet_access_mode(self, internet_access_mode):
        """
        :param str internet_access_mode: The internet access mode of the instances created in this virtual network. Accepts "YES", "NO", "EGRESS_ONLY". Defaults to "YES"
        """
        if internet_access_mode not in ["YES", "NO", "EGRESS_ONLY"]:
            raise ValueError(
                'internet_access_mode should be either "YES", "NO", or "EGRESS_ONLY"'
            )

        self.data["internetAccessMode"] = internet_access_mode
        return self

    def with_default_values(self):
        """
        Setup the VPC and Subnet to with the default values: the vpc and subnet of the FM instance
        """
        self.use_default_values = True
        return self


class FMAWSVirtualNetworkCreator(FMVirtualNetworkCreator):
    def with_vpc(self, aws_vpc_id, aws_subnet_id):
        """
        Setup the VPC and Subnet to with the VirtualNetwork

        :param str aws_vpc_id: ID of the VPC to use
        :param str aws_subnet_id: ID of the subnet to use
        """
        self.data["awsVpcId"] = aws_vpc_id
        self.data["awsSubnetId"] = aws_subnet_id
        return self

    def with_auto_create_security_groups(self):
        """
        Automatically create the AWS Security Groups when creating this VirtualNetwork
        """
        self.data["awsAutoCreateSecurityGroups"] = True
        return self

    def with_aws_security_groups(self, *aws_security_groups):
        """
        Use pre-created AWS Security Groups

        :param str *aws_security_groups: Up to 5 security group ids to assign to the instances created in this virtual network.
        """
        self.data["awsAutoCreateSecurityGroups"] = False
        self.data["awsSecurityGroups"] = aws_security_groups
        return self

    def create(self):
        """
        Create the VirtualNetwork

        :return: Created VirtualNetwork
        :rtype: :class:`dataikuapi.fm.virtualnetworks.FMAWSVirtualNetwork`
        """
        vn = self.client._perform_tenant_json(
            "POST", "/virtual-networks", body=self.data, params={ 'useDefaultValues':self.use_default_values }
        )
        return FMAWSVirtualNetwork(self.client, vn)


class FMAzureVirtualNetworkCreator(FMVirtualNetworkCreator):
    def with_azure_virtual_network(self, azure_vn_id, azure_subnet_id):
        """
        Setup the Azure Virtual Network and Subnet to with the VirtualNetwork

        :param str azure_vn_id: Resource ID of the Azure Virtual Network to use
        :param str azure_subnet_id: Resource ID of the subnet to use
        """
        self.data["azureVnId"] = azure_vn_id
        self.data["azureSubnetId"] = azure_subnet_id
        return self

    def with_auto_update_security_groups(self, auto_update_security_groups=True):
        """
        Auto update the security groups of the Azure Virtual Network

        :param boolean auto_update_security_groups: Optional, Auto update the subnet security group. Defaults to True
        """
        self.data["azureAutoUpdateSecurityGroups"] = auto_update_security_groups
        return self

    def create(self):
        """
        Create the VirtualNetwork

        :return: Created VirtualNetwork
        :rtype: :class:`dataikuapi.fm.virtualnetworks.FMAzureVirtualNetwork`
        """
        vn = self.client._perform_tenant_json(
            "POST", "/virtual-networks", body=self.data, params={ 'useDefaultValues':self.use_default_values }
        )
        return FMAzureVirtualNetwork(self.client, vn)


class FMVirtualNetwork(object):
    def __init__(self, client, vn_data):
        self.client = client
        self.vn_data = vn_data
        self.id = self.vn_data["id"]

    def save(self):
        """
        Update the Virtual Network.
        """
        self.client._perform_tenant_empty(
            "PUT", "/virtual-networks/%s" % self.id, body=self.vn_data
        )
        self.vn_data = self.client._perform_tenant_json(
            "GET", "/virtual-networks/%s" % self.id
        )

    def delete(self):
        """
        Delete the DSS Instance Settings Template.

        :return: A :class:`~dataikuapi.fm.future.FMFuture` representing the deletion process
        :rtype: :class:`~dataikuapi.fm.future.FMFuture`
        """
        future = self.client._perform_tenant_json(
            "DELETE", "/virtual-networks/%s" % self.id
        )
        return FMFuture.from_resp(self.client, future)

    def set_fleet_management(
        self, enable, event_server=None, deployer_management="NO_MANAGED_DEPLOYER"
    ):
        """
        When enabled, all instances in this virtual network know each other and can centrally manage deployer and logs centralization

        :param boolean enable: Enable or not the Fleet Management

        :param str event_server: Optional,  Node name of the node that should act as the centralized event server for logs concentration. Audit logs of all design, deployer and automation nodes will automatically be sent there.
        :param str deployer_management: Optional, Accepts:
            - "NO_MANAGED_DEPLOYER": Do not manage the the deployer. This is the default mode.
            - "CENTRAL_DEPLOYER": Central deployer. Recommanded if you have more than one design node or may have more than one design node in the future.
            - "EACH_DESIGN_NODE": Deployer from design. Recommanded if you have a single design node and want a simpler setup.
        """

        self.vn_data["managedNodesDirectory"] = enable
        self.vn_data["eventServerNodeLabel"] = event_server
        self.vn_data["nodesDirectoryDeployerMode"] = deployer_management
        return self

    def set_https_strategy(self, https_strategy):
        """
        Set the HTTPS strategy for this virtual network

        :param object: a :class:`dataikuapi.fm.virtualnetworks.FMHTTPSStrategy`
        """
        self.vn_data.update(https_strategy)
        return self


class FMAWSVirtualNetwork(FMVirtualNetwork):
    def set_dns_strategy(
        self,
        assign_domain_name,
        aws_private_ip_zone53_id=None,
        aws_public_ip_zone53_id=None,
    ):
        """
        Set the DNS strategy for this virtual network

        :param boolean assign_domain_name: If false, don't assign domain names, use ip_only
        :param str aws_private_ip_zone53_id: Optional, AWS Only, the ID of the AWS Route53 Zone to use for private ip
        :param str aws_public_ip_zone53_id: Optional, AWS Only, the ID of the AWS Route53 Zone to use for public ip
        """

        if assign_domain_name:
            self.vn_data["dnsStrategy"] = "VN_SPECIFIC_CLOUD_DNS_SERVICE"
            self.vn_data["awsRoute53PrivateIPZoneId"] = aws_private_ip_zone53_id
            self.vn_data["awsRoute53PublicIPZoneId"] = aws_public_ip_zone53_id
        else:
            self.vn_data["dnsStrategy"] = "NONE"

        return self


class FMAzureVirtualNetwork(FMVirtualNetwork):
    def set_dns_strategy(self, assign_domain_name, azure_dns_zone_id=None):
        """
        Set the DNS strategy for this virtual network

        :param boolean assign_domain_name: If false, don't assign domain names, use ip_only
        :param str azure_dns_zone_id: Optional, Azure Only, the ID of the Azure DNS zone to use
        """

        if assign_domain_name:
            self.vn_data["dnsStrategy"] = "VN_SPECIFIC_CLOUD_DNS_SERVICE"
            self.vn_data["azureDnsZoneId"] = azure_dns_zone_id
        else:
            self.vn_data["dnsStrategy"] = "NONE"

        return self


class FMHTTPSStrategy(dict):
    def __init__(self, data, https_strategy, http_redirect=False):
        """
        A class holding HTTPS Strategy for Virtual Network

        Do not create this directly, use:
            - :meth:`dataikuapi.fm.virtualnetwork.FMHTTPSStrategy.disable` to use HTTP only
            - :meth:`dataikuapi.fm.virtualnetwork.FMHTTPSStrategy.self_signed` to use self-signed certificates
            - :meth:`dataikuapi.fm.virtualnetwork.FMHTTPSStrategy.custom_cert` to use custom certificates
            - :meth:`dataikuapi.fm.virtualnetwork.FMHTTPSStrategy.lets_encrypt` to use Let's Encrypt
        """
        super(FMHTTPSStrategy, self).__init__(data)
        self["httpsStrategy"] = https_strategy
        if http_redirect:
            self["httpStrategy"] = "REDIRECT"
        else:
            self["httpStrategy"] = "DISABLE"

    @staticmethod
    def disable():
        """
        Use HTTP only
        """
        return FMHTTPSStrategy({}, "NONE", False)

    @staticmethod
    def self_signed(http_redirect):
        """
        Use self-signed certificates

        :param bool http_redirect: If true, HTTP is redirected to HTTPS. If false, HTTP is disabled. Defaults to false
        """
        return FMHTTPSStrategy({}, "SELF_SIGNED", http_redirect)

    @staticmethod
    def custom_cert(http_redirect):
        """
        Use a custom certificate for each instance

        :param bool http_redirect: If true, HTTP is redirected to HTTPS. If false, HTTP is disabled. Defaults to false
        """
        return FMHTTPSStrategy({}, "CUSTOM_CERTIFICATE", http_redirect)

    @staticmethod
    def lets_encrypt(contact_mail):
        """
        Use Let's Encrypt to generate https certificates

        :param str contact_mail: The contact email provided to Let's Encrypt
        """
        return FMHTTPSStrategy({"contactMail": contact_mail}, "LETSENCRYPT", True)
