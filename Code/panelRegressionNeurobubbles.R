

#Load libraries
library(nlme)
library(CADFtest)
library(readr)
library(dplyr)
library(ggplot2)
library(lme4) # for mixed-effects models
library(readxl)
library(tidyr)
library(openxlsx)
library(zoo)
library(reshape2)
library(gridExtra) # For arranging the two plots
library(plm)
library(lmtest)
library(sandwich)
library(forecast)
library(FinTS)
library(urca)
library(writexl)
library(scales)
library(car) # for VIF

rm(list=ls())
setwd('~/Desktop/Caltech/Neurofinance/data/')

# Function to replace NA with the first available non-NA value in the column (for forecast columns)
replace_na_with_first_value <- function(x) {
  first_non_na <- x[which(!is.na(x))[1]]  # Find the first non-NA value in the column
  x[is.na(x)] <- first_non_na  # Replace all NA values with the first available non-NA value
  return(x)
}

# Function to shift a column in a matrix or dataframe by a specified number of rows
shift_column <- function(df, column_name, shift_by) {
  if (shift_by > 0) {
    # Create a vector of NA values to add at the beginning of the column
    na_pad <- rep(NA, shift_by)
    # Shift the column down by the specified amount, adding NA values at the start
    df[[column_name]] <- c(na_pad, df[[column_name]][1:(nrow(df) - shift_by)])
  }
  return(df)
}


# Define a function to perform autocorrelation, heteroskedasticity, and normality tests for panel data models
perform_panel_diagnostics <- function(model) {
  cat("\nModel Diagnostics for Panel Data:\n")
  
  # 1. Durbin-Watson test for autocorrelation of residuals (panel data version)
  dw_test <- pdwtest(model)
  print(dw_test)
  if(dw_test$p.value < 0.05) {
    cat("The Durbin-Watson test indicates the presence of autocorrelation in the residuals.\n")
    cat("Consider using Newey-West standard errors to correct for autocorrelation.\n\n")
  } else {
    cat("No autocorrelation detected by the Durbin-Watson test.\n\n")
  }
  
  # 2. Breusch-Pagan test for heteroskedasticity (panel data version)
  bp_test <- bptest(model)
  print(bp_test)
  if(bp_test$p.value < 0.05) {
    cat("The Breusch-Pagan test indicates the presence of heteroskedasticity.\n")
    cat("Consider using heteroskedasticity-consistent standard errors (e.g., White's robust standard errors) to correct for heteroskedasticity.\n\n")
  } else {
    cat("No heteroskedasticity detected by the Breusch-Pagan test.\n\n")
  }
  
  # 3. Ljung-Box test for autocorrelation at multiple lags
  lb_test <- Box.test(residuals(model), lag = 10, type = "Ljung-Box")
  print(lb_test)
  if(lb_test$p.value < 0.05) {
    cat("The Ljung-Box test indicates the presence of autocorrelation at multiple lags in the residuals.\n")
    cat("Consider using Newey-West standard errors or an ARIMA model to correct for autocorrelation.\n\n")
  } else {
    cat("No autocorrelation detected at multiple lags by the Ljung-Box test.\n\n")
  }
  
  # 4. ARCH test for autoregressive conditional heteroskedasticity
  arch_test <- ArchTest(residuals(model), lags = 10)
  print(arch_test)
  if(arch_test$p.value < 0.05) {
    cat("The ARCH test indicates the presence of autoregressive conditional heteroskedasticity in the residuals.\n")
    cat("Consider using a GARCH model to correct for conditional heteroskedasticity.\n\n")
  } else {
    cat("No autoregressive conditional heteroskedasticity detected by the ARCH test.\n\n")
  }
}

###### 0. LOAD DATA ######
# Load the data
data <- read_csv('/Users/mihai/Documents/GitHub/neurobubbles/econometrics/flattened_data_w_bio.csv')

# Add market_id
data <- data %>%
  mutate(market_id = dense_rank(session))

unique_sessions = unique(data$session)
print(unique_sessions)


# Calculate averages of data across participants for each market and round
averaged_data_per_market <- data %>%
  group_by(market_id, round) %>%
  summarise(
    average_eda_ton_mean = mean(eda_ton_mean, na.rm = TRUE),
    average_hr_ton_mean = mean(hr_ton_mean, na.rm = TRUE),
    average_bvp_ton_mean = mean(bvp_ton_mean, na.rm = TRUE),
    average_temp_ton_mean = mean(temp_ton_mean, na.rm = TRUE),
    average_dose_r = mean(pl_dose_r, na.rm = TRUE),   
    average_dose_mu = mean(pl_dose_mu, na.rm = TRUE),
    average_pl_f0 = mean(pl_f0, na.rm = TRUE),
    average_pl_f1 = mean(pl_f1, na.rm = TRUE),
    average_pl_f2 = mean(pl_f2, na.rm = TRUE),
    average_pl_f3 = mean(pl_f3, na.rm = TRUE),
    average_volume = mean(volume, na.rm = TRUE),
    average_price = mean(price, na.rm = TRUE),
    average_log_returns = mean(log_returns, na.rm = TRUE)
  ) %>%
  ungroup()


# De-trend temp variable after averaging across participants in each market
# Step 1: Fit the regression model to de-trend the market-level average temperature
temp_trend_model <- lm(average_temp_ton_mean ~ round, data = averaged_data_per_market)

# Step 2: Extract the residuals (de-trended market-level temperature)
averaged_data_per_market$residual_temp <- residuals(temp_trend_model)

# Step 3: Replace the original `average_temp_ton_mean` with the de-trended values (residuals)
averaged_data_per_market <- averaged_data_per_market %>%
  mutate(average_temp_ton_mean = residual_temp) %>%
  select(-residual_temp)  # Optionally remove the `residual_temp` column

# Now `averaged_data_per_market` has the de-trended temperature under the same name (average_temp_ton_mean)

## Shift data for forecast columns
averaged_data_per_market <- averaged_data_per_market %>%
  group_by(market_id) %>%
  mutate(
    average_pl_f1 = shift_column(cur_data(), "average_pl_f1", 2)[["average_pl_f1"]],  # Shift by 2 rounds
    average_pl_f2 = shift_column(cur_data(), "average_pl_f2", 5)[["average_pl_f2"]],  # Shift by 5 rounds
    average_pl_f3 = shift_column(cur_data(), "average_pl_f3", 10)[["average_pl_f3"]]  # Shift by 10 rounds
  ) %>%
  ungroup()


# Replace values
averaged_data_per_market <- averaged_data_per_market %>%
  group_by(market_id) %>%
  mutate(
    # Shift the forecast columns and replace NA values with the first available value
    average_pl_f1 = replace_na_with_first_value(lag(average_pl_f1, 2)),  # Shift and replace for pl_f1
    average_pl_f2 = replace_na_with_first_value(lag(average_pl_f2, 5)),  # Shift and replace for pl_f2
    average_pl_f3 = replace_na_with_first_value(lag(average_pl_f3, 10))  # Shift and replace for pl_f3
  ) %>%
  ungroup()

# Function to calculate moving averages
calculate_moving_averages <- function(df, k) {
  df %>%
    group_by(market_id) %>%
    mutate(
      ma_eda = rollmean(average_eda_ton_mean, k = k, fill = NA, align = 'right'),
      ma_hr = rollmean(average_hr_ton_mean, k = k, fill = NA, align = 'right'),
      ma_bvp = rollmean(average_bvp_ton_mean, k = k, fill = NA, align = 'right'),
      ma_temp = rollmean(average_temp_ton_mean, k = k, fill = NA, align = 'right'),
      ma_dose_r = rollmean(average_dose_r, k = k, fill = NA, align = 'right'),
      ma_dose_mu =rollmean(average_dose_mu, k = k, fill = NA, align = 'right')
    ) %>%
    ungroup()
}

# Calculate MA3 and MA5
averaged_data_ma3 <- calculate_moving_averages(averaged_data_per_market, 3)
averaged_data_ma5 <- calculate_moving_averages(averaged_data_per_market, 5)

# standardize variables (not using them so far)
averaged_data_ma3_std <- averaged_data_ma3 %>%
  group_by(market_id) %>%
  mutate(across(c(average_eda_ton_mean, average_hr_ton_mean, average_bvp_ton_mean, average_temp_ton_mean, average_dose_r, average_dose_mu), 
                ~ (.-mean(.)) / sd(.))) %>%
  ungroup()

averaged_data_ma5_std <- averaged_data_ma5 %>%
  group_by(market_id) %>%
  mutate(across(c(average_eda_ton_mean, average_hr_ton_mean, average_bvp_ton_mean, average_temp_ton_mean, average_dose_r, average_dose_mu), 
                ~ (.-mean(.)) / sd(.))) %>%
  ungroup()


########################
### Panel regression ###
########################

library(plm)
pdata_ma3 <- pdata.frame(averaged_data_ma3, index = c("market_id", "round")) # Set up the panel data structure
pdata_ma3$round <- as.numeric(as.character(pdata_ma3$round)) 
pdata_ma3$round_squared <- pdata_ma3$round^2 # Create a squared round and add it back in data
pdata_ma3$remaining_rounds <- 30 - pdata_ma3$round
pdata_ma3$remaining_rounds_squared <- pdata_ma3$remaining_rounds^2

# Run the fixed effects model
fe_model_ma3 <- plm(average_log_returns ~ lag(average_volume,1) + ma_dose_r + average_pl_f0 + ma_eda + ma_hr + ma_temp + remaining_rounds + remaining_rounds_squared, #lag(average_dose_r,1)
                data = pdata_ma3, model = "within")
summary(fe_model_ma3) # Summary of the fixed effects model

perform_panel_diagnostics(fe_model_ma3)

#### Correct for autocorrelation and heteroskedasticity
nw_se_model_ma3 <- coeftest(fe_model_ma3, vcov = vcovNW(fe_model_ma3))
print(nw_se_model_ma3)

# Clustered standard errors (e.g., clustered by market_id)
cluster_se_model_ma3 <- coeftest(fe_model_ma3, vcov = vcovHC(fe_model_ma3, type = "HC1", cluster = "group"))
print(cluster_se_model_ma3)

# White's robust standard errors
robust_se_model_ma3 <- coeftest(fe_model_ma3, vcov = vcovHC(fe_model_ma3, type = "HC1"))
print(robust_se_model_ma3)

# Feasible Generalized Least Squares (FGLS)
fe_gls_model_ma3 <- plm(average_log_returns ~ lag(average_volume,1) + average_pl_f0 + lag(average_dose_r,1) + ma_eda + ma_hr + ma_temp + remaining_rounds + remaining_rounds_squared, #lag(average_dose_r,1) 
                    data = pdata_ma3, model = "random", effect = "individual")

summary(fe_gls_model_ma3)

# Mixed effects model with random intercepts for markets
mixed_model_ma3 <- lmer(average_log_returns ~ lag(average_volume,1) + average_pl_f0 + lag(average_dose_r,1) + ma_eda + ma_hr + ma_temp + remaining_rounds + remaining_rounds_squared + (1 | market_id), data = pdata_ma3)
summary(mixed_model_ma3)


### MA5
pdata_ma5 <- pdata.frame(averaged_data_ma5, index = c("market_id", "round")) # Set up the panel data structure
pdata_ma5$round <- as.numeric(as.character(pdata_ma5$round)) 
pdata_ma5$round_squared <- pdata_ma5$round^2 # Create a squared round and add it back in data
pdata_ma5$remaining_rounds <- 30 - pdata_ma5$round
pdata_ma5$remaining_rounds_squared <- pdata_ma5$remaining_rounds^2

# Run the fixed effects model
fe_model_ma5 <- plm(average_log_returns ~  lag(average_volume,1) + average_pl_f0 + lag(average_dose_r,1) + ma_eda + ma_hr + ma_temp + remaining_rounds + remaining_rounds_squared,
                    data = pdata_ma5, model = "within")
summary(fe_model_ma5) # Summary of the fixed effects model

perform_panel_diagnostics(fe_model_ma5)

#### Correct for autocorrelation and heteroskedasticity
nw_se_model_ma5 <- coeftest(fe_model_ma5, vcov = vcovNW(fe_model_ma5))
print(nw_se_model_ma5)

# Clustered standard errors (e.g., clustered by market_id)
cluster_se_model_ma5 <- coeftest(fe_model_ma5, vcov = vcovHC(fe_model_ma5, type = "HC1", cluster = "group"))
print(cluster_se_model_ma5)

# White's robust standard errors
robust_se_model_ma5 <- coeftest(fe_model_ma5, vcov = vcovHC(fe_model_ma5, type = "HC1"))
print(robust_se_model_ma5)

# Feasible Generalized Least Squares (FGLS)
fe_gls_model_ma5 <- plm(average_log_returns ~ lag(average_volume,1) + average_pl_f0 + lag(average_dose_r,1) + ma_eda + ma_hr + ma_temp + remaining_rounds + remaining_rounds_squared,
                        data = pdata_ma5, model = "random", effect = "individual")

summary(fe_gls_model_ma5)

# Mixed effects model with random intercepts for markets
mixed_model_ma5 <- lmer(average_log_returns ~ lag(average_volume,1) + average_pl_f0 + lag(average_dose_r,1) + ma_eda + ma_hr + ma_temp + remaining_rounds + remaining_rounds_squared + (1 | market_id), data = pdata_ma3)
summary(mixed_model_ma5)



#### PCA analysis
# Step 1: Perform PCA on the biometric data
biometric_data <- averaged_data_per_market %>%
  select(average_eda_ton_mean, average_hr_ton_mean, average_temp_ton_mean) # average_bvp_ton_mean

pca_result <- prcomp(biometric_data, center = TRUE, scale. = TRUE)

# Step 2: View the loadings (contribution of each variable to the principal components)
loadings <- pca_result$rotation
print("Loadings (Contribution of variables to PCs):")
print(loadings)

# Step 3: Calculate the proportion of variance explained by each principal component
explained_variance <- pca_result$sdev^2 / sum(pca_result$sdev^2)
print("Explained variance by each component:")
print(explained_variance)

# Step 4: Calculate the cumulative variance explained
cumulative_variance <- cumsum(explained_variance)
print("Cumulative variance explained by the components:")
print(cumulative_variance)

# Step 5: Select the number of components that explain up to 80% of the variance
num_components <- max(which(cumulative_variance <= 0.80))

# Extract the first 'num_components' principal components that account for at least 80% of the variance
principal_components <- pca_result$x[, 1:num_components]

# Print the number of components and their corresponding cumulative variance
cat("Number of components selected: ", num_components, "\n")
cat("These components explain ", round(cumulative_variance[num_components] * 100, 2), "% of the variance.\n")

# Step 6: Add the selected principal components back to the dataset for regression
# Name them PC1, PC2, PC3.
for (i in 1:num_components) {
  averaged_data_per_market[[paste0("PC", i)]] <- principal_components[, i]
}

# Function to calculate moving averages
calculate_moving_averages_pca <- function(df, k) {
  df %>%
    group_by(market_id) %>%
    mutate(
      ma_pc1 = rollmean(PC1, k = k, fill = NA, align = 'right'),
      ma_pc2 = rollmean(PC2, k = k, fill = NA, align = 'right'),
      #ma_pc3 = rollmean(PC3, k = k, fill = NA, align = 'right'),
      ma_dose_r = rollmean(average_dose_r, k = k, fill = NA, align = 'right'),
      ma_dose_mu =rollmean(average_dose_mu, k = k, fill = NA, align = 'right')
    ) %>%
    ungroup()
}

# Calculate MA3 and MA5
averaged_data_ma3_pca <- calculate_moving_averages_pca(averaged_data_per_market, 3)
averaged_data_ma5_pca <- calculate_moving_averages_pca(averaged_data_per_market, 5)

# Effects panel regression
pdata_ma3_pca <- pdata.frame(averaged_data_ma3_pca, index = c("market_id", "round")) # Set up the panel data structure
pdata_ma3_pca$round <- as.numeric(as.character(pdata_ma3_pca$round)) 
pdata_ma3_pca$round_squared <- pdata_ma3_pca$round^2 # Create a squared round and add it back in data
pdata_ma3_pca$remaining_rounds <- 30 - pdata_ma3_pca$round
pdata_ma3_pca$remaining_rounds_squared <- pdata_ma3_pca$remaining_rounds^2


# Run the fixed effects model
fe_model_ma3_pca <- plm(average_log_returns ~ + lag(average_volume,1) + average_pl_f0 + lag(average_dose_r,1) + ma_pc1 + ma_pc2 + remaining_rounds + remaining_rounds_squared,
                    data = pdata_ma3_pca, model = "within")
summary(fe_model_ma3_pca) # Summary of the fixed effects model

#### Correct for autocorrelation and heteroskedasticity
nw_se_model_ma3_pca <- coeftest(fe_model_ma3_pca, vcov = vcovNW(fe_model_ma3_pca))
print(nw_se_model_ma3_pca)

# White's robust standard errors
robust_se_model_ma3_pca <- coeftest(fe_model_ma3_pca, vcov = vcovHC(fe_model_ma3_pca, type = "HC1"))
print(robust_se_model_ma3_pca)


### Hausmann test: Fixed vs Random effects 
# First run a random effects model
re_model_ma3_pca <- plm(average_log_returns ~ lag(average_volume,1) + average_pl_f3 + lag(average_dose_r,1) + ma_pc1 + ma_pc2 + remaining_rounds + remaining_rounds_squared,
                            data = pdata_ma3_pca, model = "random", effect = "individual")

summary(re_model_ma3_pca)
hausman_test <- phtest(fe_model_ma3_pca, re_model_ma3_pca)
print(hausman_test) # If p-value <5%, then random effects model doesnt hold and we should use fixed efffects because the variables are correlated with


## Omit NA values or impute using median
pdata_ma3_pca_clean <- pdata_ma3_pca %>%
  mutate(across(everything(), ~ ifelse(is.na(.), median(., na.rm = TRUE), .)))

# Feasible Generalized Least Squares (FGLS)
fe_gls_model_pca_ma3 <- plm(average_log_returns ~ lag(average_volume,1) + average_pl_f0 + lag(average_dose_r,1) + ma_pc1 + ma_pc2 + remaining_rounds + remaining_rounds_squared,
                        data = pdata_ma3_pca_clean, model = "within") #model = "random", effect = "individual", model="within"

summary(fe_gls_model_pca_ma3)


### MA5
pdata_ma5_pca <- pdata.frame(averaged_data_ma5_pca, index = c("market_id", "round")) # Set up the panel data structure
pdata_ma5_pca$round <- as.numeric(as.character(pdata_ma5_pca$round)) 
pdata_ma5_pca$round_squared <- pdata_ma5_pca$round^2 # Create a squared round and add it back in data
pdata_ma5_pca$remaining_rounds <- 30 - pdata_ma5_pca$round
pdata_ma5_pca$remaining_rounds_squared <- pdata_ma5_pca$remaining_rounds^2


# Run the fixed effects model
fe_model_ma5_pca <- plm(average_log_returns ~ + lag(average_volume,1) + average_pl_f0 + ma_dose_r + ma_pc1 + ma_pc2 + remaining_rounds + remaining_rounds_squared,
                        data = pdata_ma5_pca, model = "within")
summary(fe_model_ma5_pca) # Summary of the fixed effects model

#### Correct for autocorrelation and heteroskedasticity
nw_se_model_ma5_pca <- coeftest(fe_model_ma5_pca, vcov = vcovNW(fe_model_ma5_pca))
print(nw_se_model_ma5_pca)

# White's robust standard errors
robust_se_model_ma5_pca <- coeftest(fe_model_ma5_pca, vcov = vcovHC(fe_model_ma5_pca, type = "HC1"))
print(robust_se_model_ma5_pca)

### Hausmann test: Fixed vs Random effects 
# First run a random effects model
re_model_ma5_pca <- plm(average_log_returns ~ lag(average_volume,1) + average_pl_f2 + lag(average_dose_r,1) + ma_pc1 + ma_pc2 + remaining_rounds + remaining_rounds_squared,
                        data = pdata_ma5_pca, model = "random", effect = "individual")

hausman_test <- phtest(fe_model_ma5_pca, re_model_ma5_pca)
print(hausman_test) # random effects model is no good 

## Impute NA values with median
pdata_ma5_pca_clean <- pdata_ma5_pca %>%
  mutate(across(everything(), ~ ifelse(is.na(.), median(., na.rm = TRUE), .)))

## Correct for autocorr and heteroskedasticity using feasible GLS
fe_gls_model_pca_ma5 <- plm(average_log_returns ~ lag(average_volume,1) + average_pl_f0 + lag(average_dose_r,1) + ma_pc1 + ma_pc2 + remaining_rounds + remaining_rounds_squared,
                            data = pdata_ma5_pca_clean, model = "within") #model = "random", effect = "individual", model="within"

summary(fe_gls_model_pca_ma5)


### Write data to Excel
# Write multiple datasets to different sheets in a single Excel file
write.xlsx(list(pdata_ma3_pca = pdata_ma3_pca, 
                pdata_ma5_pca = pdata_ma5_pca, 
                #pdata_ma3_pca_clean = pdata_ma3_pca_clean,
                #pdata_ma5_pca_clean = pdata_ma5_pca_clean,
                pdata_ma3 = pdata_ma3, 
                pdata_ma5 = pdata_ma5), 
           file = "data_19markets_panel_570obs.xlsx")


###### Plots ######
# Step 1: Average all PCA values and biometric data across all markets for MA3 and MA5
averaged_pca_biometric_ma3 <- pdata_ma3_pca %>%
  group_by(round) %>%
  summarise(
    avg_PC1 = mean(PC1, na.rm = TRUE),
    avg_PC2 = mean(PC2, na.rm = TRUE),
    #avg_PC3 = mean(PC3, na.rm = TRUE),
    avg_eda = mean(average_eda_ton_mean, na.rm = TRUE),
    avg_hr = mean(average_hr_ton_mean, na.rm = TRUE),
    avg_bvp = mean(average_bvp_ton_mean, na.rm = TRUE),
    avg_temp = mean(average_temp_ton_mean, na.rm = TRUE),
    avg_price = mean(average_price, na.rm = TRUE)
  )

## MA5
averaged_pca_biometric_ma5 <- pdata_ma5_pca %>%
  group_by(round) %>%
  summarise(
    avg_PC1 = mean(PC1, na.rm = TRUE),
    avg_PC2 = mean(PC2, na.rm = TRUE),
    #avg_PC3 = mean(PC3, na.rm = TRUE),
    avg_eda = mean(average_eda_ton_mean, na.rm = TRUE),
    avg_hr = mean(average_hr_ton_mean, na.rm = TRUE),
    avg_bvp = mean(average_bvp_ton_mean, na.rm = TRUE),
    avg_temp = mean(average_temp_ton_mean, na.rm = TRUE),
    avg_price = mean(average_price, na.rm = TRUE)
  )

# Re scale PCA
average_pca_data <- averaged_pca_biometric_ma3 %>%
  mutate(
    scaled_PC1 = avg_PC1 * (max(avg_price) / 1.8),
    scaled_PC2 = avg_PC2 * (max(avg_price) / 1.8),
    #scaled_PC3 = avg_PC3 * (max(avg_price) / 1.8)
  )

# Plot PCA components with market price for MA3 using the scaled PCA values
pca_plot_ma3 <- ggplot() +
  geom_line(data = average_pca_data %>% slice(3:n()),
            aes(x = round, y = avg_price), color = "black", size = 1.5, linetype = "solid") +
  labs(title = "Average Market Price and PCA Components (MA3)",
       x = "Round",
       y = "Average Market Price") +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 20),
    axis.title.x = element_text(size = 16),
    axis.title.y = element_text(size = 16),
    axis.text.x = element_text(size = 14),
    axis.text.y = element_text(size = 14)
  ) +
  # Use the scaled PCA components for plotting
  geom_line(data = average_pca_data, aes(x = round, y = scaled_PC1, color = "PC1"), size = 0.5, linetype = "solid") +
  geom_line(data = average_pca_data, aes(x = round, y = scaled_PC2, color = "PC2"), size = 0.5, linetype = "dashed") +
  #geom_line(data = average_pca_data, aes(x = round, y = scaled_PC3, color = "PC3"), size = 0.5, linetype = "dotted") +
  scale_y_continuous(
    name = "Average Market Price",
    sec.axis = sec_axis(~ ., name = "PCA Component Values")  # No need to rescale the secondary axis now, since it's already scaled
  ) +
  scale_color_manual(
    name = "PCA Component", 
    values = c("PC1" = "blue", "PC2" = "red"),
    labels = c("PCA Component 1", "PCA Component 2")
  ) +
  theme(
    axis.title.y.right = element_text(size = 16),
    legend.position = "bottom",
    legend.title = element_text(size = 16),
    legend.text = element_text(size = 14)
  )

print(pca_plot_ma3)

## Biometric data MA3
# Rescale the biometric data for comparison with market price
biometric_data_ma3 <- averaged_pca_biometric_ma3 %>%
  mutate(
    scaled_eda = avg_eda * (max(avg_price) / 1.2),
    scaled_hr = avg_hr * (max(avg_price) / 1.2),
    scaled_temp = avg_temp * (max(avg_price) / 1.2)
  )

# Plot biometric data with market price for MA3
biometric_plot_ma3 <- ggplot() +
  geom_line(data = biometric_data_ma3 %>% slice(3:n()),
            aes(x = round, y = avg_price), color = "black", size = 1.5, linetype = "solid") +
  labs(title = "Average Market Price and Biometric Data (MA3)",
       x = "Round",
       y = "Average Market Price") +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 20),
    axis.title.x = element_text(size = 16),
    axis.title.y = element_text(size = 16),
    axis.text.x = element_text(size = 14),
    axis.text.y = element_text(size = 14)
  ) +
  # Use the scaled biometric data for plotting
  geom_line(data = biometric_data_ma3, aes(x = round, y = scaled_eda, color = "EDA"), size = 0.5, linetype = "solid") +
  geom_line(data = biometric_data_ma3, aes(x = round, y = scaled_hr, color = "HR"), size = 0.5, linetype = "dashed") +
  geom_line(data = biometric_data_ma3, aes(x = round, y = scaled_temp, color = "TEMP"), size = 0.5, linetype = "dotted") +
  scale_y_continuous(
    name = "Average Market Price",
    sec.axis = sec_axis(~ ., name = "Biometric Data Values")
  ) +
  scale_color_manual(
    name = "Biometric Data", 
    values = c("EDA" = "blue", "HR" = "red", "TEMP" = "green"),
    labels = c("EDA", "HR", "TEMP")
  ) +
  theme(
    axis.title.y.right = element_text(size = 16),
    legend.position = "bottom",
    legend.title = element_text(size = 16),
    legend.text = element_text(size = 14)
  )

# Display biometric plot for MA3
print(biometric_plot_ma3)


### PCA MA5 graph
# Rescale the PCA components proportionally to the max average price
average_pca_data_ma5 <- averaged_pca_biometric_ma5 %>%
  mutate(
    scaled_PC1 = avg_PC1 * (max(avg_price) / 1.8),
    scaled_PC2 = avg_PC2 * (max(avg_price) / 1.8),
    #scaled_PC3 = avg_PC3 * (max(avg_price) / 1.8)
  )

# Plot PCA components with market price for MA5 using the scaled PCA values
pca_plot_ma5 <- ggplot() +
  geom_line(data = average_pca_data_ma5%>% slice(5:n()),
            aes(x = round, y = avg_price), color = "black", size = 1.5, linetype = "solid") +
  labs(title = "Average Market Price and PCA Components (MA5)",
       x = "Round",
       y = "Average Market Price") +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 20),
    axis.title.x = element_text(size = 16),
    axis.title.y = element_text(size = 16),
    axis.text.x = element_text(size = 14),
    axis.text.y = element_text(size = 14)
  ) +
  # Use the scaled PCA components for plotting
  geom_line(data = average_pca_data_ma5, aes(x = round, y = scaled_PC1, color = "PC1"), size = 0.5, linetype = "solid") +
  geom_line(data = average_pca_data_ma5, aes(x = round, y = scaled_PC2, color = "PC2"), size = 0.5, linetype = "dashed") +
  #geom_line(data = average_pca_data_ma5, aes(x = round, y = scaled_PC3, color = "PC3"), size = 0.5, linetype = "dotted") +
  scale_y_continuous(
    name = "Average Market Price",
    sec.axis = sec_axis(~ ., name = "PCA Component Values")
  ) +
  scale_color_manual(
    name = "PCA Component", 
    values = c("PC1" = "blue", "PC2" = "red"),
    labels = c("PCA Component 1", "PCA Component 2")
  ) +
  theme(
    axis.title.y.right = element_text(size = 16),
    legend.position = "bottom",
    legend.title = element_text(size = 16),
    legend.text = element_text(size = 14)
  )

# Display PCA plot for MA5
print(pca_plot_ma5)


# Rescale the biometric data for comparison with market price (MA5)
biometric_data_ma5 <- averaged_pca_biometric_ma5 %>%
  mutate(
    scaled_eda = avg_eda * (max(avg_price) / 1.8),
    scaled_hr = avg_hr * (max(avg_price) / 1.8),
    scaled_temp = avg_temp * (max(avg_price) / 1.8)
  )

# Plot biometric data with market price for MA5
biometric_plot_ma5 <- ggplot() +
  geom_line(data = biometric_data_ma5 %>% slice(5:n()), 
            aes(x = round, y = avg_price), color = "black", size = 1.5, linetype = "solid") +
  labs(title = "Average Market Price and Biometric Data (MA5)",
       x = "Round",
       y = "Average Market Price") +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 20),
    axis.title.x = element_text(size = 16),
    axis.title.y = element_text(size = 16),
    axis.text.x = element_text(size = 14),
    axis.text.y = element_text(size = 14)
  ) +
  # Use the scaled biometric data for plotting
  geom_line(data = biometric_data_ma5, aes(x = round, y = scaled_eda, color = "EDA"), size = 0.5, linetype = "solid") +
  geom_line(data = biometric_data_ma5, aes(x = round, y = scaled_hr, color = "HR"), size = 0.5, linetype = "dashed") +
  geom_line(data = biometric_data_ma5, aes(x = round, y = scaled_temp, color = "TEMP"), size = 0.5, linetype = "dotted") +
  scale_y_continuous(
    name = "Average Market Price",
    sec.axis = sec_axis(~ ., name = "Biometric Data Values")
  ) +
  scale_color_manual(
    name = "Biometric Data", 
    values = c("EDA" = "blue", "HR" = "red", "TEMP" = "green"),
    labels = c("EDA", "HR", "TEMP")
  ) +
  theme(
    axis.title.y.right = element_text(size = 16),
    legend.position = "bottom",
    legend.title = element_text(size = 16),
    legend.text = element_text(size = 14)
  )

# Display biometric plot for MA5
print(biometric_plot_ma5)



### Correlation matrix
library(corrr)
library(dplyr)

# Assuming you have your data in 'pdata_ma3_pca' or similar dataframe
# Select the relevant variables from the regression model
variables_for_correlation <- pdata_ma3_pca %>%
  select(
    average_log_returns,
    average_volume, 
    average_pl_f0, 
    average_pl_f1, 
    average_pl_f2,
    average_pl_f3, 
    average_dose_r,
    ma_pc1, 
    ma_pc2
  )

# Calculate the correlation matrix
correlation_matrix_pca <- correlate(variables_for_correlation, use = "complete.obs")

# Print the correlation matrix in a readable format
correlation_matrix_pca %>% 
  fashion() %>% 
  print()

# correlation biometric
variables_for_correlation_bio <- pdata_ma3 %>%
  select(
    average_log_returns,
    average_volume, 
    average_pl_f0, 
    average_pl_f1, 
    average_pl_f2,
    average_pl_f3, 
    average_dose_r,
    ma_hr, 
    ma_bvp,
    ma_eda, 
    ma_temp, 
  )

# Calculate the correlation matrix
correlation_matrix_biometric <- correlate(variables_for_correlation_bio, use = "complete.obs")

# Write correlation results into Excel
# Convert correlation matrices to data frames
correlation_matrix_pca_df <- correlation_matrix_pca %>% fashion() %>% as.data.frame()
correlation_matrix_biometric_df <- correlation_matrix_biometric %>% fashion() %>% as.data.frame()

# Write both correlation matrices into an Excel file with separate sheets
write_xlsx(
  list(
    PCA_Correlation_Matrix = correlation_matrix_pca_df,
    Biometric_Correlation_Matrix = correlation_matrix_biometric_df
  ),
  path = "correlation_matrices.xlsx"
)
