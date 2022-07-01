"""Code to coordinate identifying edges between principals in an AWS account"""

#  Copyright (c) NCC Group and Erik Steringer 2019. This file is part of Principal Mapper.
#
#      Principal Mapper is free software: you can redistribute it and/or modify
#      it under the terms of the GNU Affero General Public License as published by
#      the Free Software Foundation, either version 3 of the License, or
#      (at your option) any later version.
#
#      Principal Mapper is distributed in the hope that it will be useful,
#      but WITHOUT ANY WARRANTY; without even the implied warranty of
#      MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#      GNU Affero General Public License for more details.
#
#      You should have received a copy of the GNU Affero General Public License
#      along with Principal Mapper.  If not, see <https://www.gnu.org/licenses/>.

import logging
import os
import traceback
from concurrent import futures
from typing import List, Optional

import botocore.session

from principalmapper.common import Edge, Node
from principalmapper.graphing.autoscaling_edges import AutoScalingEdgeChecker
from principalmapper.graphing.cloudformation_edges import CloudFormationEdgeChecker
from principalmapper.graphing.codebuild_edges import CodeBuildEdgeChecker
from principalmapper.graphing.ec2_edges import EC2EdgeChecker
from principalmapper.graphing.iam_edges import IAMEdgeChecker
from principalmapper.graphing.lambda_edges import LambdaEdgeChecker
from principalmapper.graphing.sagemaker_edges import SageMakerEdgeChecker
from principalmapper.graphing.ssm_edges import SSMEdgeChecker
from principalmapper.graphing.sts_edges import STSEdgeChecker


logger = logging.getLogger(__name__)


# Externally referable dictionary with all the supported edge-checking types
checker_map = {
    'autoscaling': AutoScalingEdgeChecker,
    'cloudformation': CloudFormationEdgeChecker,
    'codebuild': CodeBuildEdgeChecker,
    'ec2': EC2EdgeChecker,
    'iam': IAMEdgeChecker,
    'lambda': LambdaEdgeChecker,
    'sagemaker': SageMakerEdgeChecker,
    'ssm': SSMEdgeChecker,
    'sts': STSEdgeChecker
}


def obtain_edges(session: 'botocore.session.Session', checker_list: List[str], nodes: List[Node], region_allow_list: Optional[List[str]] = None,
                 region_deny_list: Optional[List[str]] = None, scps: Optional[List[List[dict]]] = None,
                 client_args_map: Optional[dict] = None) -> List[Edge]:
    """Given a list of nodes and a botocore Session, return a list of edges between those nodes. Only checks
    against services passed in the checker_list param. """
    results = []
    logger.info('Initiating edge checks.')
    logger.debug('Services being checked for edges: {}'.format(checker_list))

    jobs = []
    with futures.ProcessPoolExecutor(max_workers=int(os.cpu_count()/2)) as ppool:
        with futures.ThreadPoolExecutor() as tpool:
            checks = [checker_map[chk](ppool) for chk in checker_list if chk in checker_map]

            for chk in checks:
                jobs.append(tpool.submit(chk.return_edges, nodes, region_allow_list, region_deny_list, scps, client_args_map, session))

        for job in futures.as_completed(jobs):
            exc = job.exception()
            if exc:
                raise exc
            results.extend(job.result())

    return results
