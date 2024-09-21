import sys
import os
sys.path.append("../")
from pyCruncher.AgentDeepSeek import AgentDeepSeek

def test_fim_completion():
    agent = AgentDeepSeek( base_url="https://api.deepseek.com/beta" )
    
    # prefix = "def fibonacci(n):\n"
    # suffix = "    return fib(n-1) + fib(n-2)\n"
    # content = agent.fim_completion(prefix, suffix)
    # print( prefix + content + suffix)

    # prefix = """
    # double getLenardJones( Vec3d d, Vec3d& f, double R0, double E0 ){
    #     double r = d.norm();
    # """

    prefix = """
    double getLenardJones( Vec3d d, Vec3d& f, double R0, double E0 ){
        double inv_r = 1.0/d.norm();
        double u     = R0*inv_r;
    """

    suffix = """
    	f = d*(dE_dr/r);
        return E;
    };
    """
    content = agent.fim_completion(prefix, suffix)
    print( prefix + content + suffix)

if __name__ == '__main__':
    test_fim_completion()
