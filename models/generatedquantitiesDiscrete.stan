// generated quantities

generated quantities {
    int y_proj[n_weeks,n_ostates];
    real llx[n_weeks,n_ostates];
    real ll_ = 0; // log-likelihood for model
    //real R0 = beta[1]/(sigc[1]+sigmau);

    {

      for (i in 1:n_weeks) {
      if (dC[i] > 1e7 || dR[i] > 1e7 || dD[i] > 1e7 || dC[i] < 0 || dR[i] < 0 || dD[i] < 0 || is_nan(-dC[i]) || is_nan(-dR[i])|| is_nan(-dD[i]))
      {
        y_proj[i,1] = 0;
        y_proj[i,2] = 0;
        y_proj[i,3] = 0;
        }
      else
        y_proj[i,1] = scale*neg_binomial_2_rng(min([dC[i],1e6]),max([phi,.01]));
        y_proj[i,2] = scale*neg_binomial_2_rng(min([dR[i],1e6]),max([phi,.01]));
        y_proj[i,3] = scale*neg_binomial_2_rng(min([dD[i],1e6]),max([phi,.01]));

        if (y[i,1] > -1)
          llx[i,1] = neg_binomial_2_lpmf(y[i,1]/scale| min([dC[i],1e6]),max([phi,.01]));
        else
          llx[i,1] =0.;

        if (y[i,2] > -1)
          llx[i,2] = neg_binomial_2_lpmf(y[i,2]/scale| min([dR[i],1e6]),max([phi,.01]));
        else
          llx[i,2] =0.;

        if (y[i,3] > -1)
          llx[i,3] = neg_binomial_2_lpmf(y[i,3]/scale| min([dD[i],1e6]),max([phi,.01]));
        else
          llx[i,3] =0.;

        ll_ += llx[i,1] + llx[i,2] + llx[i,3];
      }
    }

}
