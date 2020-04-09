#save compartment models here as classes
#text description + Stan C++ code as string + networkx + maybe latex
import matplotlib.pyplot as plt
plt.ion()
import numpy as np
import networkx as nx



class model_sir1: 
    def __init__(self):
        self.name = "sir1"
        self.descript = """
        About: \n
        SIR model - expects I only \n
        fits I (assumes I=C) only
        """
        print(self.descript)
        #initialize model specific parameters expected by Stan code
        self.stan_data = {
            'n_theta':2,
            'n_difeq':3,
            'n_ostates':3
            }
        self.math = """
        \begin{align} 
        \dot{dS} &= -\beta S I \\
        \dot{dI} &= \beta S I - \gamma I\\
        \dot{dR} &= \gamma I
         \end{align}
        """
        self.stan = """
            functions {
              real[] SIR(real t,  // time
              real[] u,           // system state {susceptible, infected, recovered}
              real[] theta,       // parameters 
              real[] x_r,
              int[] x_i) {

              real du_dt[3];

              real beta = theta[1];
              real gamma = theta[2];

              real S = u[1];  # susceptible
              real I = u[2];  # infected
              real R = u[3];  # recovered

              du_dt[1] = -beta*S*I; //dS  
              du_dt[2] = beta*S*I - gamma*I; //dI
              du_dt[3] = gamma*I; //dR  

              return du_dt;
              }
            }

            data {
              int<lower = 1> n_obs;       // number of days observed
              int<lower = 1> n_theta;     // number of model parameters
              int<lower = 1> n_difeq;     // number of differential equations for yhat
              int<lower = 1> n_ostates;     // number of observed states
              int<lower = 1> n_pop;       // population
              real<lower = 1> n_scale;       // scale to match observed scale
              int y[n_obs,n_ostates];           // data, per-day-tally [cases,recovered,death]
              real t0;                // initial time point 
              real ts[n_obs];         // time points that were observed
            }

            transformed data {
                real x_r[0];
                int x_i[0];
            }

            parameters {
                real<lower = 0> theta[n_theta]; // model parameters 
            }

            transformed parameters{
                real u[n_obs, n_difeq]; // solution from the ODE solver
                real u_init[3];     // initial conditions f


                u_init[1] = 1;  //S
                u_init[2] = y[1,1]/n_scale; //I(C)
                u_init[3] = 0; //RD

                u = integrate_ode_rk45(SIR, u_init, t0, ts, theta, x_r, x_i);

            }

            model {
                real lambda[n_obs]; //poisson parameter [cases, recovered_dead]

                //priors
                
                theta[1] ~ lognormal(log(0.25),1); //beta
                theta[2] ~ lognormal(log(0.1),1); //gamma
               
                //likelihood
                for (i in 1:n_obs){
                    lambda[i] = u[i,2]*n_scale; // I (C)
                    target += poisson_lpmf(y[i,1]|max([lambda[i],0.0]));
                }
            }

        generated quantities {
            real R_0;      // Basic reproduction number
            real ll_lambda[n_obs]; //poisson parameter [cases, recover/death]
            real ll_[n_obs]; // log-likelihood for model
            
            real ll_beta = theta[1];
            real ll_gamma = theta[2];
            
            R_0 = ll_beta/ll_gamma;
            
            for (i in 1:n_obs){
                ll_lambda[i] = u[i,2]*n_scale; //cases
                ll_[i] = poisson_lpmf(y[i,1]|max([ll_lambda[i],0.0]));
                
            }
        }
        """
    def plotnetwork(self):
        print("S: susceptible")
        print("I: infected")
        print("RD: recovered_dead")

        G = nx.DiGraph()
        G.add_node('S')
        G.add_node('I')
        G.add_node('RD')

        G.add_edges_from([('S','I'),('I','RD')])
        nx.draw(G,with_labels=True)
        return
    


class model_sir2: 
    def __init__(self):
        self.name = "sir2"
        self.descript = """
        About: \n
        SIR model - expects I,R,D; sums R and D columns \n
        fits I (assumes I=C) and RD
        """
        print(self.descript)
        #initialize model specific parameters expected by Stan code
        self.stan_data = {
            'n_theta':2,
            'n_difeq':3,
            'n_ostates':3
            }
        self.math = """
        \begin{align} 
        \dot{dS} &= -\beta S I \\
        \dot{dI} &= \beta S I - \gamma I\\
        \dot{dR} &= \gamma I
         \end{align}
        """
        self.stan = """
            functions {
              real[] SIR(real t,  // time
              real[] u,           // system state {susceptible, infected, recovered}
              real[] theta,       // parameters 
              real[] x_r,
              int[] x_i) {

              real du_dt[3];

              real beta = theta[1];
              real gamma = theta[2];

              real S = u[1];  # susceptible
              real I = u[2];  # infected
              real R = u[3];  # recovered

              du_dt[1] = -beta*S*I; //dS  
              du_dt[2] = beta*S*I - gamma*I; //dI
              du_dt[3] = gamma*I; //dR  

              return du_dt;
              }
            }

            data {
              int<lower = 1> n_obs;       // number of days observed
              int<lower = 1> n_theta;     // number of model parameters
              int<lower = 1> n_difeq;     // number of differential equations for yhat
              int<lower = 1> n_ostates;     // number of observed states
              int<lower = 1> n_pop;       // population
              real<lower = 1> n_scale;       // scale to match observed scale
              int y[n_obs,n_ostates];           // data, per-day-tally [cases,recovered,death]
              real t0;                // initial time point 
              real ts[n_obs];         // time points that were observed
            }

            transformed data {
                real x_r[0];
                int x_i[0];
            }

            parameters {
                real<lower = 0> theta[n_theta]; // model parameters 
            }

            transformed parameters{
                real u[n_obs, n_difeq]; // solution from the ODE solver
                real u_init[3];     // initial conditions f


                u_init[1] = 1;  //S
                u_init[2] = y[1,1]/n_scale; //I(C)
                u_init[3] = (y[1,2]+y[1,3])/n_scale; //RD

                u = integrate_ode_rk45(SIR, u_init, t0, ts, theta, x_r, x_i);

            }

            model {
                real lambda[n_obs,2]; //poisson parameter [cases, recovered_dead]

                //priors
                
                theta[1] ~ lognormal(log(0.25),1); //beta
                theta[2] ~ lognormal(log(0.1),1); //gamma
               
                //likelihood
                for (i in 1:n_obs){
                    lambda[i,1] = u[i,2]*n_scale; // I (C)
                    lambda[i,2] = u[i,3]*n_scale; //RD


                    target += poisson_lpmf(y[i,1]|max([lambda[i,1],0.0]));
                    target += poisson_lpmf(y[i,2]+y[i,3]|max([lambda[i,2],0.0]));
                }
            }

        generated quantities {
            real R_0;      // Basic reproduction number
            real ll_lambda[n_obs,n_ostates-1]; //poisson parameter [cases, recover/death]
            real ll_[n_obs]; // log-likelihood for model
            
            real ll_beta = theta[1];
            real ll_gamma = theta[2];
            
            R_0 = ll_beta/ll_gamma;
            
            for (i in 1:n_obs){
                ll_lambda[i,1] = u[i,2]*n_scale; //cases
                ll_lambda[i,2] = u[i,3]*n_scale; //recovered + death
                
                ll_[i] = poisson_lpmf(y[i,1]|max([ll_lambda[i,1],0.0]));
                ll_[i] += poisson_lpmf(y[i,2]+y[i,3]|max([ll_lambda[i,2],0.0]));
                
            }
        }
        """
    def plotnetwork(self):
        print("S: susceptible")
        print("I: infected")
        print("RD: recovered_dead")

        G = nx.DiGraph()
        G.add_node('S')
        G.add_node('I')
        G.add_node('RD')

        G.add_edges_from([('S','I'),('I','RD')])
        nx.draw(G,with_labels=True)
        return
    
class model_sicu:
    def __init__(self):
        self.name = "sicu"
        self.descript = """
        About: \n
        SICU model \n
        Some unknown I and known C, both go to recovered and death \n
        I and C have same leak to R and D but I leak is to unknown U
        """
        print(self.descript)
        #initialize model specific parameters expected by Stan code
        self.stan_data = {
            'n_theta':4,
            'n_difeq':4,
            'n_ostates':3
            }
#         self.math = """
#         """
        self.stan = """
        functions {
            real[] SIR(real t,  // time
            real[] u,           // system state {infected,cases,susceptible}
            real[] theta,       // parameters 
            real[] x_r,
            int[] x_i) {

            real du_dt[4];

            real sigmac = theta[1];
            real sigma = theta[2];
            real beta = theta[3];
            
            real C = u[1];  # cases
            real I = u[3];  # unknown infected
            real S = u[4];  # susceptible

            du_dt[1] = sigmac*I - sigma*C; // dC = 
            du_dt[2] = sigma*C; //dRD = 
            du_dt[3] = beta*(I)*S - sigmac*I - sigma*I; //dI = 
            du_dt[4] = -beta*(I)*S; //dS = 
            
            //I goes to a leak variable U with rate sigma that is not followed
            
            return du_dt;
          }
        }

        data {
          int<lower = 1> n_obs;       // number of days observed
          int<lower = 1> n_theta;     // number of model parameters
          int<lower = 1> n_difeq;     // number of differential equations for yhat
          int<lower = 1> n_ostates;     // number of observed states
          int<lower = 1> n_pop;       // population
          real<lower = 1> n_scale;       // scale to match observed scale
          int y[n_obs,n_ostates];           // data, per-day-tally [cases,recovered,death]
          real t0;                // initial time point 
          real ts[n_obs];         // time points that were observed
        }

        transformed data {
            real x_r[0];
            int x_i[0];           
        }

        parameters {
            real<lower = 0> theta[n_theta]; // model parameters 
        }

        transformed parameters{
            real u[n_obs, n_difeq]; // solution from the ODE solver
            real u_init[4];     // initial conditions 
            
            real sigmaci = theta[1];
            real sigmai = theta[2];
            real betai = theta[3];
            real theta_init = theta[4];
           
            u_init[1] = y[1,1]/n_scale; //C
            u_init[2] = (y[1,2] + y[1,3])/n_scale; // U = R + D
            u_init[3] = (betai - sigmai)/sigmaci * u_init[1] + theta_init/n_scale; // I
            u_init[4] = 1-betai/sigmaci*u_init[1]; // S
            
            u = integrate_ode_rk45(SIR, u_init, t0, ts, theta, x_r, x_i);
           //u = integrate_ode_bdf(SIR, u_init, t0, ts, theta, x_r, x_i);

        }

        model {
            real lambda[n_obs,n_ostates-1]; //poisson parameter [cases, deaths, recovered]

            //priors
            //S0 ~ beta(2, 2); //some prior for between 0 and 1 fraction of the population
            theta[1] ~ lognormal(log(0.1),1); //sigmac
            theta[2] ~ lognormal(log(0.1),1); //sigma
            theta[3] ~ lognormal(log(0.25),1); //beta
            theta[4] ~ lognormal(log(0.1),1); // initial condition uncertainty
            
            

            //likelihood
            for (i in 1:n_obs){
                lambda[i,1] = u[i,1]*n_scale; //cases
                lambda[i,2] = u[i,2]*n_scale; //recovered + death
                
                target += poisson_lpmf(y[i,1]|max([lambda[i,1],0.0]));
                target += poisson_lpmf(y[i,2]+y[i,3]|max([lambda[i,2],0.0]));
                
            }

        }

        generated quantities {
            real R_0;      // Basic reproduction number
            real ll_lambda[n_obs,n_ostates-1]; //poisson parameter [cases, recover/death]
            real ll_[n_obs]; // log-likelihood for model
            
            real ll_sigmac = theta[1];
            real ll_sigma = theta[2];
            real ll_beta = theta[3];
            
            R_0 = ll_beta/(ll_sigma+ll_sigmac);
            
            for (i in 1:n_obs){
                ll_lambda[i,1] = u[i,1]*n_scale; //cases
                ll_lambda[i,2] = u[i,2]*n_scale; //recovered + death
                
                ll_[i] = poisson_lpmf(y[i,1]|max([ll_lambda[i,1],0.0]));
                ll_[i] += poisson_lpmf(y[i,2]+y[i,3]|max([ll_lambda[i,2],0.0]));
                
            }
        }
        """
    def plotnetwork(self):
        print("S: susceptible")
        print("I: infected")
        print("C: identified cases")
        print("R: recovered")
        print("D: dead")
        print("U: unknown recovered/dead")
        G = nx.DiGraph()
        G.add_node('S')
        G.add_node('I')
        G.add_node('C')
        G.add_node('U')
        G.add_node('RD')
        G.add_edges_from([('S','I'),('I','S'),('I','C'),('C','S'),('I','U'),('C','RD')])
        nx.draw(G,with_labels=True)
        return

class model_sicuf:
    def __init__(self):
        self.name = "sicuf"
        self.descript = """
        About: \n
        SICU model \n
        Some unknown I and known C, both go to recovered and death\n
        I and C have same leak to R and D\n
        I leak is to unknown U with different rate than C to RD
        """
        print(self.descript)
        #initialize model specific parameters expected by Stan code
        self.stan_data = {
            'n_theta':5,
            'n_difeq':4,
            'n_ostates':3
            }
#         self.math = """
#         """
        self.stan = """
        functions {
            real[] SIR(real t,  // time
            real[] u,           // system state {infected,cases,susceptible}
            real[] theta,       // parameters 
            real[] x_r,
            int[] x_i) {

            real du_dt[4];

            real sigmac = theta[1];
            real sigma = theta[2];
            real beta = theta[3];
            real f = theta[4];
            
            real C = u[1];  # cases
            real I = u[3];  # unknown infected
            real S = u[4];  # susceptible

            du_dt[1] = sigmac*I - sigma*C; // dC = 
            du_dt[2] = sigma*C; //dRD = 
            du_dt[3] = beta*(I)*S - sigmac*I - f*sigma*I; //dI = 
            du_dt[4] = -beta*(I)*S; //dS = 
            
            //I goes to a leak variable U with rate f*sigma that is not followed
            
            return du_dt;
          }
        }

        data {
          int<lower = 1> n_obs;       // number of days observed
          int<lower = 1> n_theta;     // number of model parameters
          int<lower = 1> n_difeq;     // number of differential equations for yhat
          int<lower = 1> n_ostates;     // number of observed states
          int<lower = 1> n_pop;       // population
          real<lower = 1> n_scale;       // scale to match observed scale
          int y[n_obs,n_ostates];           // data, per-day-tally [cases,recovered,death]
          real t0;                // initial time point 
          real ts[n_obs];         // time points that were observed
        }

        transformed data {
            real x_r[0];
            int x_i[0];           
        }

        parameters {
            real<lower = 0> theta[n_theta]; // model parameters 
        }

        transformed parameters{
            real u[n_obs, n_difeq]; // solution from the ODE solver
            real u_init[4];     // initial conditions 
            
            real sigmaci = theta[1];
            real sigmai = theta[2];
            real betai = theta[3];
            real theta_init = theta[5];
           
            u_init[1] = y[1,1]/n_scale; //C
            u_init[2] = (y[1,2] + y[1,3])/n_scale; // U = R + D
            u_init[3] = (betai - sigmai)/sigmaci * u_init[1] + theta_init/n_scale; // I
            u_init[4] = 1-betai/sigmaci*u_init[1]; // S
            
            u = integrate_ode_rk45(SIR, u_init, t0, ts, theta, x_r, x_i);
           //u = integrate_ode_bdf(SIR, u_init, t0, ts, theta, x_r, x_i);

        }

        model {
            real lambda[n_obs,n_ostates-1]; //poisson parameter [cases, deaths, recovered]

            //priors
            //S0 ~ beta(2, 2); //some prior for between 0 and 1 fraction of the population
            theta[1] ~ lognormal(log(0.1),1); //sigmac
            theta[2] ~ lognormal(log(0.1),1); //sigma
            theta[3] ~ lognormal(log(0.25),1); //beta
            theta[4] ~ lognormal(log(0.1),1); //f
            theta[5] ~ lognormal(log(0.1),1); // initial condition uncertainty
            
            

            //likelihood
            for (i in 1:n_obs){
                lambda[i,1] = u[i,1]*n_scale; //cases
                lambda[i,2] = u[i,2]*n_scale; //recovered + death
                
                target += poisson_lpmf(y[i,1]|max([lambda[i,1],0.0]));
                target += poisson_lpmf(y[i,2]+y[i,3]|max([lambda[i,2],0.0]));
                
            }

        }

        generated quantities {
            real R_0;      // Basic reproduction number
            real ll_lambda[n_obs,n_ostates-1]; //poisson parameter [cases, recover/death]
            real ll_[n_obs]; // log-likelihood for model
            
            real ll_sigmac = theta[1];
            real ll_sigma = theta[2];
            real ll_beta = theta[3];
            
            R_0 = ll_beta/(ll_sigma+ll_sigmac);
            
            for (i in 1:n_obs){
                ll_lambda[i,1] = u[i,1]*n_scale; //cases
                ll_lambda[i,2] = u[i,2]*n_scale; //recovered + death
                
                ll_[i] = poisson_lpmf(y[i,1]|max([ll_lambda[i,1],0.0]));
                ll_[i] += poisson_lpmf(y[i,2]+y[i,3]|max([ll_lambda[i,2],0.0]));
                
            }
        }
        """
    def plotnetwork(self):
        print("S: susceptible")
        print("I: infected")
        print("C: identified cases")
        print("R: recovered")
        print("D: dead")
        print("U: unknown recovered/dead")
        G = nx.DiGraph()
        G.add_node('S')
        G.add_node('I')
        G.add_node('C')
        G.add_node('U')
        G.add_node('RD')
        G.add_edges_from([('S','I'),('I','S'),('I','C'),('C','S'),('I','U'),('C','RD')])
        nx.draw(G,with_labels=True)
        return
 


class model_sicuq:
    def __init__(self):
        self.name = "sicuq"
        self.descript = """
        About: \n
        SICUQ model \n
        Some unknown I and known C, both go to recovered and death \n
        I and C have same leak to R and D but I leak is to unknown U
        """
        print(self.descript)
        #initialize model specific parameters expected by Stan code
        self.stan_data = {
            'n_theta':5,
            'n_difeq':4,
            'n_ostates':3
            }
#         self.math = """
#         """
        self.stan = """
        functions {
            real[] SIR(real t,  // time
            real[] u,           // system state {infected,cases,susceptible}
            real[] theta,       // parameters 
            real[] x_r,
            int[] x_i) {

            real du_dt[4];

            real sigmac = theta[1];
            real sigma = theta[2];
            real beta = theta[3];
            real q = theta[4];
            
            real C = u[1];  # cases
            real I = u[3];  # unknown infected
            real S = u[4];  # susceptible

            du_dt[1] = sigmac*I - sigma*C; // dC = 
            du_dt[2] = sigma*C; //dRD = 
            du_dt[3] = beta*(I+q*C)*S - sigmac*I - sigma*I; //dI = 
            du_dt[4] = -beta*(I+q*C)*S; //dS = 
            
            //I goes to a leak variable U with rate sigma that is not followed
            
            return du_dt;
          }
        }

        data {
          int<lower = 1> n_obs;       // number of days observed
          int<lower = 1> n_theta;     // number of model parameters
          int<lower = 1> n_difeq;     // number of differential equations for yhat
          int<lower = 1> n_ostates;     // number of observed states
          int<lower = 1> n_pop;       // population
          real<lower = 1> n_scale;       // scale to match observed scale
          int y[n_obs,n_ostates];           // data, per-day-tally [cases,recovered,death]
          real t0;                // initial time point 
          real ts[n_obs];         // time points that were observed
        }

        transformed data {
            real x_r[0];
            int x_i[0];           
        }

        parameters {
            real<lower = 0> theta[n_theta]; // model parameters 
        }

        transformed parameters{
            real u[n_obs, n_difeq]; // solution from the ODE solver
            real u_init[4];     // initial conditions 
            
            real sigmaci = theta[1];
            real sigmai = theta[2];
            real betai = theta[3];
            real theta_init = theta[5];
           
            u_init[1] = y[1,1]/n_scale; //C
            u_init[2] = (y[1,2] + y[1,3])/n_scale; // U = R + D
            u_init[3] = (betai - sigmai)/sigmaci * u_init[1] + theta_init/n_scale; // I
            u_init[4] = 1-betai/sigmaci*u_init[1]; // S
            
            u = integrate_ode_rk45(SIR, u_init, t0, ts, theta, x_r, x_i);
           //u = integrate_ode_bdf(SIR, u_init, t0, ts, theta, x_r, x_i);

        }

        model {
            real lambda[n_obs,n_ostates-1]; //poisson parameter [cases, deaths, recovered]

            //priors
            //S0 ~ beta(2, 2); //some prior for between 0 and 1 fraction of the population
            theta[1] ~ lognormal(log(0.1),1); //sigmac
            theta[2] ~ lognormal(log(0.1),1); //sigma
            theta[3] ~ lognormal(log(0.25),1); //beta
            theta[4] ~ lognormal(log(0.1),1); //q
            theta[5] ~ lognormal(log(0.1),1); // initial condition uncertainty
            
            

            //likelihood
            for (i in 1:n_obs){
                lambda[i,1] = u[i,1]*n_scale; //cases
                lambda[i,2] = u[i,2]*n_scale; //recovered + death
                
                target += poisson_lpmf(y[i,1]|max([lambda[i,1],0.0]));
                target += poisson_lpmf(y[i,2]+y[i,3]|max([lambda[i,2],0.0]));
                
            }

        }

        generated quantities {
            real R_0;      // Basic reproduction number
            real ll_lambda[n_obs,n_ostates-1]; //poisson parameter [cases, recover/death]
            real ll_[n_obs]; // log-likelihood for model
            
            real ll_sigmac = theta[1];
            real ll_sigma = theta[2];
            real ll_beta = theta[3];
            
            R_0 = ll_beta/(ll_sigma+ll_sigmac);
            
            for (i in 1:n_obs){
                ll_lambda[i,1] = u[i,1]*n_scale; //cases
                ll_lambda[i,2] = u[i,2]*n_scale; //recovered + death
                
                ll_[i] = poisson_lpmf(y[i,1]|max([ll_lambda[i,1],0.0]));
                ll_[i] += poisson_lpmf(y[i,2]+y[i,3]|max([ll_lambda[i,2],0.0]));
                
            }
        }
        """
    def plotnetwork(self):
        print("S: susceptible")
        print("I: infected")
        print("C: identified cases")
        print("R: recovered")
        print("D: dead")
        print("U: unknown recovered/dead")
        G = nx.DiGraph()
        G.add_node('S')
        G.add_node('I')
        G.add_node('C')
        G.add_node('U')
        G.add_node('RD')
        G.add_edges_from([('S','I'),('I','S'),('I','C'),('C','S'),('I','U'),('C','RD')])
        nx.draw(G,with_labels=True)
        return


    
class model_sicrq:
    def __init__(self):
        self.name = "sicrq"
        self.descript = """
        About: \n
        SICRDq model \n
        Some unknown I and known C, both go to recovered and death \n
        I and C have same leak to r and d but different to total infected Z
        """
        print(self.descript)
        #initialize model specific parameters expected by Stan code
        self.stan_data = {
            'n_theta':6,
            'n_difeq':5,
            'n_ostates':3
            }
#         self.math = """
#         \begin{eqnarray}
#         \frac{dC}{dt} &=& \sigma_c I - (\sigma_r + \sigma_d) C &\qquad\qquad &  
#         \frac{dD}{dt} &=& \sigma_d C\\
#         \frac{dR}{dt} &=& \sigma_r C &\qquad\qquad & 
#         \frac{dI}{dt} &=& \beta (I+qC) S - (\sigma_c  + \sigma_r + \sigma_d) I \\
#         \frac{dZ}{dt} &=& - \beta (I+qC) S  &\qquad\qquad & 
#         \end{eqnarray}
#         """
        self.stan = """
        functions {
            real[] SIR(real t,  // time
            real[] u,           // system state {infected,cases,susceptible}
            real[] theta,       // parameters 
            real[] x_r,
            int[] x_i) {

            real du_dt[5];

            real sigmac = theta[1];
            real sigmar = theta[2];
            real sigmad =  theta[3];
            real q = theta[4]; 
            real beta = theta[5];
            
            real C = u[1];  # cases
            real I = u[4];  # unknown infected
            real S = u[5];  # susceptible

            du_dt[1] = sigmac*I - (sigmar + sigmad)*C; // dC  
            du_dt[2] = sigmar*C; // dR 
            du_dt[3] = sigmad*C; // dD  
            du_dt[4] = beta*(I+q*C)*S - (sigmac + sigmar + sigmad)*I; // dI  
            du_dt[5] = -beta*(I+q*C)*S; // dS
            
            return du_dt;
          }
        }

        data {
          int<lower = 1> n_obs;       // number of days observed
          int<lower = 1> n_theta;     // number of model parameters
          int<lower = 1> n_difeq;     // number of differential equations for yhat
          int<lower = 1> n_ostates;     // number of observed states
          int<lower = 1> n_pop;       // population
          real<lower = 1> n_scale;       // scale to match observed scale
          int y[n_obs,n_ostates];           // data, per-day-tally [cases,recovered,death]
          real t0;                // initial time point 
          real ts[n_obs];         // time points that were observed
        }

        transformed data {
            real x_r[0];
            int x_i[0];           
        }

        parameters {
            real<lower = 0> theta[6]; // model parameters 
        }

        transformed parameters{
            real u[n_obs, n_difeq]; // solution from the ODE solver
            real u_init[5];     // initial conditions for fractions
           
            u_init[1] = y[1,1]/n_scale; //C
            u_init[2] = y[1,2]/n_scale; //R 
            u_init[3] = y[1,3]/n_scale; //D 
            u_init[4] = (theta[5] - theta[2] - theta[3] )/theta[1] * u_init[1] + theta[6]/n_scale; // I
            u_init[5] = 1-theta[5]/theta[1]*u_init[1]; // S
            
            u = integrate_ode_rk45(SIR, u_init, t0, ts, theta, x_r, x_i);
           //u = integrate_ode_bdf(SIR, u_init, t0, ts, theta, x_r, x_i);

        }

        model {
            real lambda[n_obs,3]; //poisson parameter [cases, deaths, recovered]

            //priors
            theta[1] ~ lognormal(log(0.1),10); //sigmac
            theta[2] ~ lognormal(log(0.1),10); //sigmar
            theta[3] ~ lognormal(log(0.1),10); //sigmad
            theta[4] ~ lognormal(log(0.1),10); //q
            theta[5] ~ lognormal(log(0.25),10); //beta
            theta[6] ~ lognormal(log(0.1),10); // initial condition uncertainty
            
            

            //likelihood
            for (i in 1:n_obs){
                lambda[i,1] = u[i,1]*n_scale; //cases
                lambda[i,2] = u[i,2]*n_scale; //recovered
                lambda[i,3] = u[i,3]*n_scale; //dead
                
                target += poisson_lpmf(y[i,1]|max([lambda[i,1],0.0]));
                target += poisson_lpmf(y[i,2]|max([lambda[i,2],0.0]));
                target += poisson_lpmf(y[i,3]|max([lambda[i,3],0.0]));

            }

        }

        generated quantities {
            real R_0;      // Basic reproduction number
            real ll_lambda[n_obs,n_ostates]; //poisson parameter [cases, recover/death]
            real ll_[n_obs]; // log-likelihood for model
            
            real ll_sigma = theta[1] + theta[2] + theta[3];
            real ll_beta = theta[5];
            
            R_0 = ll_beta/ll_sigma;
            
            for (i in 1:n_obs){
                ll_lambda[i,1] = u[i,1]*n_scale; //cases
                ll_lambda[i,2] = u[i,2]*n_scale; //recovered 
                ll_lambda[i,3] = u[i,3]*n_scale; //death
                
                ll_[i] = poisson_lpmf(y[i,1]|max([ll_lambda[i,1],0.0]));
                ll_[i] += poisson_lpmf(y[i,2]|max([ll_lambda[i,2],0.0]));
                ll_[i] += poisson_lpmf(y[i,3]|max([ll_lambda[i,3],0.0]));
                
            }
        }
        """
    def plotnetwork(self):
        print("S: susceptible")
        print("I: infected")
        print("C: identified cases")
        print("R: recovered")
        print("D: dead")
        G = nx.DiGraph()
        G.add_node('S')
        G.add_node('I')
        G.add_node('C')
        G.add_node('R')
        G.add_node('D')
        G.add_node('Ru')
        G.add_node('Du')
        G.add_edges_from([('S','I'),('I','C'),('I','Ru'),('I','Du'),('C','R'),('C','D')])
        nx.draw(G,with_labels=True)
        return
 


        
# class model1b:
#     def __init__(self):
#         self.descript = """
#         About: \n
#         SIR model - expects I,R,D; ignores R and D\n
#         fits I only
#         """
#         print(self.descript)
#         #initialize model specific parameters expected by Stan code
#         self.stan_data = {
#             'n_theta':2,
#             'n_difeq':3,
#             'n_ostates':3
#             }
#         self.math = """
#         \begin{align} 
#         \dot{dS} &= -\beta S I \\
#         \dot{dI} &= \beta S I - \gamma I\\
#         \dot{dR} &= \gamma I
#          \end
#          """
#         self.stan = """
#             functions {
#               real[] SIR(real t,  // time
#               real[] y,           // system state {susceptible, infected, recovered}
#               real[] theta,       // parameters 
#               real[] x_r,
#               int[] x_i) {

#               real dy_dt[3];

#               real beta = theta[1];
#               real gamma = theta[2];

#               real S = y[1];  # susceptible
#               real I = y[2];  # infected
#               real R = y[3];  # recovered

#               dy_dt[1] = -beta*S*I; //dS  
#               dy_dt[2] = beta*S*I - gamma*I; //dI
#               dy_dt[3] = gamma*I; //dR  

#               return dy_dt;
#               }
#             }

#             data {
#               int<lower = 1> n_obs;       // number of days observed
#               int<lower = 1> n_theta;     // number of model parameters
#               int<lower = 1> n_difeq;     // number of differential equations for yhat
#               int<lower = 1> n_ostates;     // number of observed states
#               int<lower = 1> n_pop;       // population 
#               int y[n_obs,n_ostates];           // data, per-day-tally [cases]
#               real t0;                // initial time point 
#               real ts[n_obs];         // time points that were observed
#             }

#             transformed data {
#               real x_r[0];
#               int x_i[0];
#               }

#             parameters {
#                 real<lower = 0> theta[n_theta]; // model parameters 
#                 real<lower = 0, upper = 1> S0;  // initial fraction of susceptible individuals
#             }

#             transformed parameters{
#                 real y_hat[n_obs, n_difeq]; // solution from the ODE solver
#                 real y_init[n_difeq];     // initial conditions for fractions

#                 y_init[1] = S0; //S
#                 y_init[2] = 1-S0; //I
#                 y_init[3] = 0; //R

#                 y_hat = integrate_ode_rk45(SIR, y_init, t0, ts, theta, x_r, x_i);

#             }

#             model {
#                 real lambda[n_obs]; //poisson parameter [cases, recovered_dead]

#                 //priors
#                 S0 ~ beta(2, 2); //some prior for between 0 and 1 fraction of the population
#                 //for (i in 1:n_theta){
#                 //    theta[i] ~ lognormal(0,1);
#                 //}

#                 // examples from Anastasia Chatzilena
#                 theta[1] ~ lognormal(0,1);
#                 theta[2] ~ gamma(0.004,0.02);  //Assume mean infectious period = 5 days 


#                 //likelihood
#                 for (i in 1:n_obs){
#                     lambda[i] = y_hat[i,2]*n_pop;
#                     //target += poisson_lpmf(y[i]|lambda[i]);
#                     }
#                     y[:,1] ~ poisson(lambda);
#             }

#               generated quantities {
#               real R_0;      // Basic reproduction number
#               R_0 = theta[1]/theta[2];
#               }
#         """
#     def plotnetwork(self):
#         print("S: susceptible")
#         print("I: infected")
#         print("RD: recovered_dead")

#         G = nx.DiGraph()
#         G.add_node('S')
#         G.add_node('I')
#         G.add_node('RD')

#         G.add_edges_from([('S','I'),('I','RD')])
#         nx.draw(G,with_labels=True)
#         return
    




# class model_sicrq_old:
#     def __init__(self):
#         self.descript = """
#         About: \n
#         SICRDq model \n
#         Some unknown I and known C, both go to recovered and death \n
#         I and C have same leak to r and d but different to total infected Z
#         """
#         print(self.descript)
#         #initialize model specific parameters expected by Stan code
#         self.stan_data = {
#             'n_theta':5,
#             'n_difeq':5,
#             'n_ostates':3
#             }
# #         self.math = """
# #         \begin{eqnarray}
# #         \frac{dC}{dt} &=& \sigma_c I - (\sigma_r + \sigma_d) C &\qquad\qquad &  
# #         \frac{dD}{dt} &=& \sigma_d C\\
# #         \frac{dR}{dt} &=& \sigma_r C &\qquad\qquad & 
# #         \frac{dI}{dt} &=& \beta (I+qC) S - (\sigma_c  + \sigma_r + \sigma_d) I \\
# #         \frac{dZ}{dt} &=& - \beta (I+qC) S  &\qquad\qquad & 
# #         \end{eqnarray}
# #         """
#         self.stan = """
#         functions {
#             real[] SIR(real t,  // time
#             real[] u,           // system state {infected,cases,susceptible}
#             real[] theta,       // parameters 
#             real[] x_r,
#             int[] x_i) {

#             real du_dt[5];

#             real sigmac = theta[1];
#             real sigmar = theta[2];
#             real sigmad =  theta[3];
#             real q = theta[4]; 
#             real beta = theta[5];
#             real N = 1;
            
#             real I = u[4];  # unknown infected
#             real C = u[1];  # cases
#             real S = u[5];  # susceptible

#             du_dt[1] = sigmac*I - (sigmar + sigmad)*C; // dC  
#             du_dt[2] = sigmad*C; // dD  
#             du_dt[3] = sigmar*C; // dR  
#             du_dt[4] = beta*N*(I+q*C)*S - (sigmac + sigmar + sigmad)*I; // dI  
#             du_dt[5] = -beta*N*(I+q*C)*S; // dS
            
#             return du_dt;
#           }
#         }

#         data {
#           int<lower = 1> n_obs;       // number of days observed
#           int<lower = 1> n_theta;     // number of model parameters
#           int<lower = 1> n_difeq;     // number of differential equations for yhat
#           int<lower = 1> n_ostates;     // number of observed states
#           int<lower = 1> n_pop;       // population
#           real<lower = 1> n_scale;       // scale to match observed scale
#           int y[n_obs,n_ostates];           // data, per-day-tally [cases,recovered,death]
#           real t0;                // initial time point 
#           real ts[n_obs];         // time points that were observed
#           int max_num_steps; 
#         }

#         transformed data {
#             real x_r[0];
#             int x_i[0];           
#         }

#         parameters {
#             real<lower = 0, upper = 1> S0;  // initial fraction of susceptible individuals
#             real<lower = 0> theta[5]; // model parameters 
            
            
#             //
#         }

#         transformed parameters{
#             real u[n_obs, n_difeq]; // solution from the ODE solver
#             real u_init[5];     // initial conditions for fractions
           
#             // yhat for model is larger than y observed
#             // also y initialized are not the same as y observed
#             // y observed are cases (C), recovered (R), and deaths (D)
#             // y init are latent infected (I), cases (C), and latent susceptible (S)

#             u_init[1] = 0; //C
#             u_init[2] = 0; //D 
#             u_init[3] = 0; //R 
#             u_init[4] = 1/n_pop; // I
#             u_init[5] = 1;//S0*n_pop/n_scale; // 
            
            
#             u = integrate_ode_rk45(SIR, u_init, t0, ts, theta, x_r, x_i);
#            //u = integrate_ode_bdf(SIR, u_init, t0, ts, theta, x_r, x_i);

#         }

#         model {
#             real lambda[n_obs,3]; //poisson parameter [cases, deaths, recovered]

#             //priors
#             S0 ~ beta(2, 2); //some prior for between 0 and 1 fraction of the population
#             theta[1] ~ lognormal(0,0.1); //sigmac
#             theta[2] ~ lognormal(0,0.1); //sigmar
#             theta[3] ~ lognormal(0,0.1); //sigmad
#             theta[4] ~ lognormal(0,0.1); //q
#             theta[5] ~ lognormal(0,0.25); //beta
#             //theta[5] ~ normal(n_scale,0.1*n_scale);
            
            

#             //likelihood
#             for (i in 1:n_obs){
#                 lambda[i,1] = u[i,1]*n_scale; //cases
#                 lambda[i,2] = u[i,3]*n_scale; //recovered
#                 lambda[i,3] = u[i,2]*n_scale; //dead
                
#                 //target += poisson_lpmf(y[i,1]|lambda[i,1]);
#                 //target += poisson_lpmf(y[i,2]|lambda[i,2]);
#                 //target += poisson_lpmf(y[i,3]|lambda[i,3]);

#                 target += poisson_lpmf(y[i,1]|max([lambda[i,1],0.0]));
#                 target += poisson_lpmf(y[i,2]|max([lambda[i,2],0.0]));
#                 target += poisson_lpmf(y[i,3]|max([lambda[i,3],0.0]));

#                 //y[i,1] ~ poisson(lambda[i,1]);
#                 //y[i,2] ~ poisson(lambda[i,2]);
#                 //y[i,3] ~ poisson(lambda[i,3]);
#             }

#         }

#         generated quantities {
#             real R_0;      // Basic reproduction number
#             R_0 = (theta[5])/(theta[1]+theta[2]+theta[3]);
#         }
#         """
#     def plotnetwork(self):
#         print("S: susceptible")
#         print("I: infected")
#         print("C: identified cases")
#         print("R: recovered")
#         print("D: dead")
#         G = nx.DiGraph()
#         G.add_node('S')
#         G.add_node('I')
#         G.add_node('C')
#         G.add_node('R')
#         G.add_node('D')
#         G.add_node('Ru')
#         G.add_node('Du')
#         G.add_edges_from([('S','I'),('I','C'),('I','Ru'),('I','Du'),('C','R'),('C','D')])
#         nx.draw(G,with_labels=True)
#         return