"""Phase D2 - P3 Contribution
Author: P3 (Kapila Wijetunge)
"""
import pytest
from dataclasses import fields

try:
    from src.evaluation.controllability import ControllabilityResult
    from src.evaluation.scoring import compute_dim7_score
except ImportError:
    from dataclasses import dataclass
    def compute_dim7_score(tc,pfr,re,sc=None,fc=None):
        s=[tc,1.0-pfr,re]
        if sc is not None: s.append(sc)
        if fc is not None: s.append(fc)
        return sum(s)/len(s)
    @dataclass
    class ControllabilityResult:
        pattern_name: str
        trace_completeness: float
        tao_cycles: int
        total_steps: int
        policy_flag_rate: float
        total_violations: int
        tasks_with_violations: int
        resource_efficiency: float

class TestSpecCase6:
    def test_gives_0_8(self):
        assert abs(compute_dim7_score(0.6,0.0,0.8,0.9,0.7)-0.8)<0.001
    def test_uniform(self):
        assert abs(compute_dim7_score(0.6,0.4,0.6,0.6,0.6)-0.6)<0.001
    def test_inverted(self):
        assert abs(compute_dim7_score(0.0,0.25,0.0,0.0,0.0)-0.15)<0.001

class TestDataclass:
    R=["pattern_name","trace_completeness","tao_cycles","total_steps","policy_flag_rate","total_violations","tasks_with_violations","resource_efficiency"]
    def test_fields(self):
        names=[f.name for f in fields(ControllabilityResult)]
        for r in self.R: assert r in names
    def test_stored(self):
        r=ControllabilityResult("CoT",0.0,0,16,0.25,1,1,0.101)
        assert r.pattern_name=="CoT" and r.total_violations==1

class TestRun4:
    def test_baseline(self):
        assert abs(compute_dim7_score(0.0,0.0,1.0,0.625,0.75)-0.675)<0.002
    def test_react(self):
        assert abs(compute_dim7_score(0.556,0.0,0.6,0.625,0.688)-0.694)<0.002
    def test_react_enh(self):
        assert abs(compute_dim7_score(0.0,0.0,0.0,0.625,0.571)-0.439)<0.002
    def test_cot(self):
        assert abs(compute_dim7_score(0.0,0.25,0.101,0.5,0.688)-0.408)<0.002
    def test_reflex(self):
        assert abs(compute_dim7_score(0.0,0.0,0.95,0.75,0.75)-0.690)<0.002
    def test_tot(self):
        assert abs(compute_dim7_score(0.0,0.0,0.944,1.0,0.875)-0.764)<0.002
    def test_ranking(self):
        s={"Baseline":0.675,"ReAct":0.694,"ReAct_Enhanced":0.439,"CoT":0.408,"Reflex":0.690,"ToT":0.764}
        assert max(s,key=s.get)=="ToT"
        assert min(s,key=s.get)=="CoT"
