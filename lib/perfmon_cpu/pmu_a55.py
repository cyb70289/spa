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

from .perfmon_cpu import PerfmonCpu
import pandas as pd
import numpy


class a55(PerfmonCpu):

    def _set_metrics(self):
        """
        Registers a list of all derived metrics available for the cpu.

        Registers plot details for the derived metrics of the cpu.
        """

        self.metric_list = ['mpki', 'stall', 'stall_frontend', 'stall_backend', 'stall_ilock', 'L2tlb', 'missrate', 'instruction_mix']

        # mpki details
        self.metric_plot_data['mpki'] = (['L1I MPKI', 'L1I_TLB MPKI', 'L1D_TLB MPKI', 'L2D_TLB MPKI', 'L1D MPKI', 'L2D MPKI', 'L3D MPKI', 'BRANCH MPKI'],
                                         'radar',
                                         'Misses Per Kilo Instructions')

        # stalls highlevel, stack is worst case scenario as front and and back end
        # stalls can occur concurrently
        self.metric_plot_data['stall'] = (['FRONT_END_STALL', 'BACKEND_STALL', 'PIPELINE_USEFUL_CYCLES'],
                                          'stacked-bar',
                                          'Stall Distribution')
        # stalls front end distribution
        self.metric_plot_data['stall_frontend'] = (['FE_CACHE_STALL', 'FE_TLB_STALL'],
                                                   'stacked-bar',
                                                   'Front End Stalls Distribution')

        # stalls back end distribution
        self.metric_plot_data['stall_backend'] = (['BE_ILOCK_STALL', 'BE_LOAD_CACHE_STALL', 'BE_LOAD_TLB_STALL', 'BE_STORE_BUFFER_STALL', 'BE_STORE_TLB_STALL'],
                                                  'stacked-bar',
                                                  'Back End Stalls Distribution')

        # stalls ilock distribution
        self.metric_plot_data['stall_ilock'] = (['BE_ILOCK_AGU_STALL', 'BE_ILOCK_FPU_STALL', 'BE_ILOCK_LOAD_STALL', 'BE_ILOCK_STORE_STALL'],
                                                'stacked-bar',
                                                'Ilock Stalls Distribution')

        # missrate details
        self.metric_plot_data['missrate'] = (['L1I Miss Rate', 'L1I_TLB Miss Rate', 'L1D_TLB Miss Rate', 'L2D_TLB Miss Rate', 'L1D Miss Rate', 'L2D Miss Rate', 'L3D Miss Rate', 'BRANCH Misprediction Rate'],
                                             'single-bar',
                                             '')  # Empty because each element name will be the title

        # TLB Performance details
        self.metric_plot_data['L2tlb'] = (['L2D_TLB_Miss_Data_%', 'L2D_TLB_Miss_Instruction_%'],
                                        'stacked-bar',
                                        'L2 TLB Miss Distribution'
                                        )

        # instruction_mix details
        self.metric_plot_data['instruction_mix'] = (['Load', 'Store', 'Integer', 'SIMD', 'FloatingPoint', 'Branch', 'Crypto'],
                                                    'stacked-bar',
                                                    'Instruction Mix')

    def derive_perfmon_metrics(self):
        '''
        Compute all derived metrics supported by the CPU.

        Return:
            (pandas.DataFrame): A new df containing all derived metric values appended
                                to input raw counter dataframe.
        '''
        mpki_df = self.metric_mpki(self.raw_df)
        stall_df = self.metric_stall(self.raw_df)
        missrate_df = self.metric_missrate(self.raw_df)
        self.raw_df = pd.concat([mpki_df, stall_df, missrate_df], axis=1)

    def metric_mpki(self, df_in):
        '''
        Calculate derived metric counter values: Misses Per Kilo Instructions - MPKI

        Args:
            df_in (pandas.DataFrame): Input df to calculate MPKI on

        Return:
            (pandas.DataFrame): A new df containing MPKI derived metric values
        '''
        df_out = pd.DataFrame(index=df_in.index)

        df_out['L1I MPKI'] = self._check_div(
            df_in, 'L1I_CACHE_REFILL', 'INST_RETIRED', dscale=1e3)
        df_out['L1I_TLB MPKI'] = self._check_div(
            df_in, 'L1I_TLB_REFILL', 'INST_RETIRED', dscale=1e3)
        df_out['L1D_TLB MPKI'] = self._check_div(
            df_in, 'L1D_TLB_REFILL', 'INST_RETIRED', dscale=1e3)
        df_out['L2D_TLB MPKI'] = self._check_div(
            df_in, 'L2D_TLB_REFILL', 'INST_RETIRED', dscale=1e3)
        df_out['L1D MPKI'] = self._check_div(
            df_in, 'L1D_CACHE_REFILL', 'INST_RETIRED', dscale=1e3)
        df_out['L2D MPKI'] = self._check_div(
            df_in, 'L2D_CACHE_REFILL', 'INST_RETIRED', dscale=1e3)
        df_out['L3D MPKI'] = self._check_div(
            df_in, 'L3D_CACHE_REFILL', 'INST_RETIRED', dscale=1e3)
        df_out['BRANCH MPKI'] = self._check_div(
            df_in, 'BR_MIS_PRED', 'INST_RETIRED', dscale=1e3)
        return df_out

    def metric_stall(self, df_in):
        '''
        Calculate derived metric counter values: Stalls

        Args:
            df_in (pandas.DataFrame): Input df to calculate Stalls on

        Return:
            (pandas.DataFrame): A new df containing Stalls derived metric values
        '''
        df_out = pd.DataFrame(index=df_in.index)

        # High level Stall Stack
        df_out['FRONT_END_STALL'] = self._check_div(df_in, 'STALL_FRONTEND', 'CPU_CYCLES').apply(self._convert_to_percent)
        df_out['BACKEND_STALL'] = self._check_div(df_in, 'STALL_BACKEND', 'CPU_CYCLES').apply(self._convert_to_percent)
        df_out['PIPELINE_USEFUL_CYCLES'] = 1 - (df_out['FRONT END STALL'] + df_out['PIPELINE USEFUL CYCLES']).apply(self._convert_to_percent)

        # Break down of Front End Stalls
        df_out['FE_CACHE_STALL'] = self._check_div(df_in, 'STALL_FRONTEND_CACHE', 'STALL_FRONTEND').apply(self._convert_to_percent)
        df_out['FE_TLB_STALL'] = self._check_div(df_in, 'STALL_FRONTEND_TLB', 'STALL_FRONTEND').apply(self._convert_to_percent)

        # Break down of Back End Stalls High Level
        df_out['BE_ILOCK_STALL'] = self._check_div(df_in, 'STALL_BACKEND_ILOCK', 'STALL_BACKEND').apply(self._convert_to_percent)
        df_out['BE_LOAD_CACHE_STALL'] = self._check_div(df_in, 'STALL_BACKEND_LD_CACHE', 'STALL_BACKEND').apply(self._convert_to_percent)
        df_out['BE_LOAD_TLB_STALL'] = self._check_div(df_in, 'STALL_BACKEND_LD_TLB', 'STALL_BACKEND').apply(self._convert_to_percent)
        df_out['BE_STORE_BUFFER_STALL'] = self._check_div(df_in, 'STALL_BACKEND_ST_STB', 'STALL_BACKEND').apply(self._convert_to_percent)
        df_out['BE_STORE_TLB_STALL'] = self._check_div(df_in, 'STALL_BACKEND_ST_TLB', 'STALL_BACKEND').apply(self._convert_to_percent)

        # Break down of Back End ILOCK STALLS
        df_out['BE_ILOCK_AGU_STALL'] = self._check_div(df_in, 'STALL_BACKEND_ILOCK_AGU', 'STALL_BACKEND_ILOCK').apply(self._convert_to_percent)
        df_out['BE_ILOCK_FPU_STALL'] = self._check_div(df_in, 'STALL_BACKEND_ILOCK_FPU', 'STALL_BACKEND_ILOCK').apply(self._convert_to_percent)
        df_out['BE_ILOCK_LOAD_STALL'] = self._check_div(df_in, 'STALL_BACKEND_ILOCK_LD', 'STALL_BACKEND_ILOCK').apply(self._convert_to_percent)
        df_out['BE_ILOCK_STORE_STALL'] = self._check_div(df_in, 'STALL_BACKEND_ILOCK_ST', 'STALL_BACKEND_ILOCK').apply(self._convert_to_percent)

        return df_out

    def metric_stall_FUWise(self, df_in):
        '''
        Calculate derived metric counter values: Stalls as % of Cycles

        Args:
            df_in (pandas.DataFrame): Input df to calculate Stalls% on

        Return:
            (pandas.DataFrame): A new df containing Stalls% derived metric values
        '''
        df_out = pd.DataFrame(index=df_in.index)

        # Detailed Stall Stack Chart, use if required later on
        df_out['FRONTEND_CACHE_STALL_%'] = self._check_div(df_in, 'STALL_FRONTEND_CACHE', 'CPU_CYCLES').apply(self._convert_to_percent)
        df_out['FRONTEND_TLB_STALL_%'] = self._check_div(df_in, 'STALL_FRONTEND_TLB', 'CPU_CYCLES').apply(self._convert_to_percent)
        df_out['BACKEND_LOAD_CACHE_STALL_%'] = self._check_div(df_in, 'STALL_BACKEND_LD_CACHE', 'CPU_CYCLES').apply(self._convert_to_percent)
        df_out['BACKEND_LOAD_TLB_STALL_%'] = self._check_div(df_in, 'STALL_BACKEND_LD_TLB', 'CPU_CYCLES').apply(self._convert_to_percent)
        df_out['BACKEND_STORE_BUFFER_STALL_%'] = self._check_div(df_in, 'STALL_BACKEND_ST_STB', 'CPU_CYCLES').apply(self._convert_to_percent)
        df_out['BACKEND_STORE_TLB_STALL_%'] = self._check_div(df_in, 'STALL_BACKEND_ST_TLB', 'CPU_CYCLES').apply(self._convert_to_percent)
        df_out['BACKEND_ILOCK_AGU_STALL_%'] = self._check_div(df_in, 'STALL_BACKEND_ILOCK_AGU', 'CPU_CYCLES').apply(self._convert_to_percent)
        df_out['BACKEND_ILOCK_FPU_STALL_%'] = self._check_div(df_in, 'STALL_BACKEND_ILOCK_FPU', 'CPU_CYCLES').apply(self._convert_to_percent)
        df_out['BACKEND_ILOCK_LOAD_STALL_%'] = self._check_div(df_in, 'STALL_BACKEND_ILOCK_LD', 'CPU_CYCLES').apply(self._convert_to_percent)
        df_out['BACKEND_ILOCK_STORE_STALL_%'] = self._check_div(df_in, 'STALL_BACKEND_ILOCK_ST', 'CPU_CYCLES').apply(self._convert_to_percent)

    def metric_missrate(self, df_in):
        '''
        Calculate derived metric counter values: Miss Rate

        Args:
            df_in (pandas.DataFrame): Input df to calculate Miss Rate on

        Return:
            (pandas.DataFrame): A new df containing Miss Rate derived metric values
        '''
        df_out = pd.DataFrame(index=df_in.index)
        df_out['L1I Miss Rate'] = self._check_div(df_in, 'L1I_CACHE_REFILL', 'L1I_CACHE').apply(self._convert_to_percent)
        df_out['L1I_TLB Miss Rate'] = self._check_div(df_in, 'L1I_TLB_REFILL', 'L1I_TLB').apply(self._convert_to_percent)
        df_out['L1D_TLB Miss Rate'] = self._check_div(df_in, 'L1D_TLB_REFILL', 'L1D_TLB').apply(self._convert_to_percent)
        df_out['L2D_TLB Miss Rate'] = self._check_div(df_in, 'L2D_TLB_REFILL', 'L2D_TLB').apply(self._convert_to_percent)
        df_out['L1D Miss Rate'] = self._check_div(df_in, 'L1D_CACHE_REFILL', 'L1D_CACHE').apply(self._convert_to_percent)
        df_out['L2D Miss Rate'] = self._check_div(df_in, 'L2D_CACHE_REFILL', 'L2D_CACHE').apply(self._convert_to_percent)
        df_out['L3D Miss Rate'] = self._check_div(df_in, 'L3D_CACHE_REFILL', 'L3D_CACHE').apply(self._convert_to_percent)
        df_out['BRANCH Misprediction Rate'] = self._check_div(df_in, 'BR_MIS_PRED', 'BR_PRED').apply(self._convert_to_percent)
        return df_out

    def metric_L2tlb(self, df_in):
        '''
        Calculate derived metric counter values: TLB Miss Details

        Args:
            df_in (pandas.DataFrame): Input df to calculate TLB Miss Details on

        Return:
            (pandas.DataFrame): A new df containing TLB Miss Details derived metric values
        '''
        df_out = pd.DataFrame(index=df_in.index)
        df_out['L2D_TLB_Miss_Data_%'] = self._check_div(df_in, 'DTLB_WALK', 'L2D_TLB_REFILL').apply(self._convert_to_percent)
        df_out['L2D_TLB_Miss_Instruction_%'] = self._check_div(df_in, 'ITLB_WALK', 'L2D_TLB_REFILL').apply(self._convert_to_percent)
        return df_out

    def metric_instruction_mix(self, df_in):
        '''
        Calculate derived metric counter values: Instruction Mix

        Args:
            df_in (pandas.DataFrame): Input df to calculate Instruction Mix on

        Return:
            (pandas.DataFrame): A new df containing Instruction Mix derived metric values
        '''

        df_out = pd.DataFrame(index=df_in.index)
        df_out['Load'] = self._check_div(df_in, 'LD_SPEC', 'INST_RETIRED')
        df_out['Store'] = self._check_div(df_in, 'ST_SPEC', 'INST_RETIRED')
        df_out['Integer'] = self._check_div(df_in, 'DP_SPEC', 'INST_RETIRED')
        df_out['SIMD'] = self._check_div(df_in, 'ASE_SPEC', 'INST_RETIRED')
        df_out['FloatingPoint'] = self._check_div(df_in, 'VFP_SPEC', 'INST_RETIRED')
        df_out['Branch'] = self._check_div(df_in, 'BR_RETIRED', 'INST_RETIRED')
        df_out['Crypto'] = self._check_div(df_in, 'CRYPTO_SPEC', 'INST_RETIRED')
        return df_out
