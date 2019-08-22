"""Code to identify if a principal in an AWS account can use access to IAM to access other principals."""

import io
import os
from typing import List

from principalmapper.common.edges import Edge
from principalmapper.common.nodes import Node
from principalmapper.graphing.edge_checker import EdgeChecker
from principalmapper.querying import query_interface


class IAMEdgeChecker(EdgeChecker):
    """Goes through the IAM service to locate potential edges between nodes."""

    def return_edges(self, nodes: List[Node], output: io.StringIO = os.devnull, debug: bool = False) -> List[Edge]:
        """Fulfills expected method return_edges."""
        result = []
        for node_source in nodes:
            for node_destination in nodes:
                # skip self-access checks
                if node_source == node_destination:
                    continue

                # check if source is an admin, if so it can access destination but this is not tracked via an Edge
                if node_source.is_admin:
                    continue

                if ':user/' in node_destination.arn:
                    # Change the user's access keys
                    access_keys_mfa = False

                    create_auth_res, mfa_res = query_interface.local_check_authorization_handling_mfa(
                        node_source,
                        'iam:CreateAccessKey',
                        node_destination.arn,
                        {},
                        debug
                    )

                    if mfa_res:
                        access_keys_mfa = True

                    if node_destination.access_keys == 2:
                        # can have a max of two access keys, need to delete before making a new one
                        auth_res, mfa_res = query_interface.local_check_authorization_handling_mfa(
                            node_source,
                            'iam:DeleteAccessKey',
                            node_destination.arn,
                            {},
                            debug
                        )
                        if not auth_res:
                            create_auth_res = False  # can't delete target access key, can't generate a new one
                        if mfa_res:
                            access_keys_mfa = True

                    if create_auth_res:
                        reason = 'can create access keys to authenticate as'
                        if access_keys_mfa:
                            reason = '(MFA required) ' + reason

                        result.append(
                            Edge(
                                node_source, node_destination, reason
                            )
                        )

                    # Change the user's password
                    if node_destination.active_password:
                        pass_auth_res, mfa_res = query_interface.local_check_authorization_handling_mfa(
                            node_source,
                            'iam:UpdateLoginProfile',
                            node_destination.arn,
                            {},
                            debug
                        )
                    else:
                        pass_auth_res, mfa_res = query_interface.local_check_authorization_handling_mfa(
                            node_source,
                            'iam:CreateLoginProfile',
                            node_destination.arn,
                            {},
                            debug
                        )
                    if pass_auth_res:
                        reason = 'can set the password to authenticate as'
                        if mfa_res:
                            reason = '(MFA required) ' + reason
                        result.append(Edge(node_source, node_destination, reason))

                if ':role/' in node_destination.arn:
                    # Change the role's trust doc
                    update_role_res, mfa_res = query_interface.local_check_authorization_handling_mfa(
                        node_source,
                        'iam:UpdateAssumeRolePolicy',
                        node_destination.arn,
                        {},
                        debug
                    )
                    if update_role_res:
                        reason = 'can update the trust document to access'
                        if mfa_res:
                            reason = '(MFA required) ' + reason
                        result.append(Edge(node_source, node_destination, reason))

        return result
