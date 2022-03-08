#!/usr/bin/python3

#    Copyright 2020 Arm Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Author: Jumana Mundichipparakkal, Tushar Singh Chouhan


from abc import ABCMeta, abstractmethod
import numpy
import pandas


class PerfmonCpu(metaclass=ABCMeta):
    """
    Base class for all CPUs whose perfmon counters are used for analysis.

    pmu_obj: data_manager object with all the pmus 

    """

    def __init__(self, pmu_obj):
        self.pmu_obj = pmu_obj

    @abstractmethod
    def derive_perfmon_metrics(self):
        """
        Creates all derived metrics for the cpu.
        """
        raise NotImplementedError()



    def _check_div(self, pmu_obj, numerator, denominator, nscale=1, dscale=1):
       '''
       Divides the numerator with denominator and return the array
       '''
       return numpy.divide(pmu_obj.info['counter'][numerator]['Value'], 
                pmu_obj.info['counter'][denominator]['Value'])*dscale
   


    def _convert_to_percent(self, x):
        """ Converts the passed value to percentage data and round to zero converting to integer.
        """
        return (x * 100)

