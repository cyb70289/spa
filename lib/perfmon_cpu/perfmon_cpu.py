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

# Author: Jumana Mundichipparakkal


from abc import ABCMeta, abstractmethod
import numpy
import pandas


class PerfmonCpu(metaclass=ABCMeta):
    """
    Base class for all CPUs whose perfmon counters are used for analysis.

    :raw_df: Dataframe with perfmon counters and derived metrics for the core.

    """
    metric_list = []  # List of metrics supported by CPU perfmon counters
    # Dictionary of tuples of metric plot data for a m
    # Key: metric
    # Value: (list of metric labels, plot type(str), title for the plot (str))
    metric_plot_data = {}

    def __init__(self, df):
        self.raw_df = df
        # Set metric details for the CPU
        self._set_metrics()

    @abstractmethod
    def derive_perfmon_metrics(self):
        """
        Creates all derived metrics for the cpu.
        """
        raise NotImplementedError()

    @abstractmethod
    def _set_metrics(self):
        """
        Registers a list of all derived metrics available for the cpu.
        """
        raise NotImplementedError()

    def _check_div(self, df, numerator, denominator, nscale=1, dscale=1):
        '''
        Helper function to safely divide one column by another, only if both exist

        Args:
            df (pandas.DataFrame): Input df to perform the divide on
            numerator (str): The column label to check whether it exists and use it
                             as the numerator in the divide
            denominator (str): The column label to check whether it exists and use
                               it as the denominator in the divide
            nscale (int): The numerator scale value. Defaults to 1
            dscale (int): The denominator scale value. Defaults to 1

        Return:
            (pandas.Series or numpy.nan): If checks pass, will return the result of
                                          the divide (with optional scaling being
                                          applied beforehand), Otherwise numpy.nan
        '''
        if all(x in df.columns for x in [numerator, denominator]):
            return (df[numerator]['Values']/df[denominator]['Values'])*dscale
        nan_data = numpy.array([numpy.nan]*len(df))
        return pandas.Series(nan_data)
    
        # return df[numerator].div(nscale).div(df[denominator].div(dscale))

    def _convert_to_percent(self, x):
        """ Converts the passed value to percentage data and round to zero converting to integer.
        """
        if numpy.isnan(x):
            return x
        if numpy.isinf(x) or numpy.isneginf(x):
            return numpy.nan
        return int(x * 100)

    def _get_metrics(self):
        """
        Returns a list of all derived metrics for the cpu.
        """
        return self.metric_list
