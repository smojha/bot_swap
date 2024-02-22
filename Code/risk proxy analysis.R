# Install packages
install.packages("openxlsx")
install.packages("zoo")

#Load libraries
library(readr)
library(dplyr)
library(ggplot2)
library(lme4) # for mixed-effects models
library(readxl)
library(tidyr)
library(openxlsx)
library(zoo)

rm(list=ls())
setwd("/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/")

# Load the data

# Pilot 5
data <- read_csv('/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_2024_02_20_online/rounds_2024-02-20.csv') # Pilot 5

# Pilot 3
data <- read_excel('/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_03_23_11_30/rounds_2023-11-30_forecast.xlsx', sheet = 'clean') # Pilot 3
# Prolific participants for pilot3 : 86T si 04R
# subject1 = 14L, rest are subject2, 3, 4

# Function to calculate consecutive risky choices (1s), consecutive safe choices (0s)
calculate_consecutive_choices <- function(choices) {
  # Initialize vectors to store lengths of consecutive choices
  consecutive_risky <- numeric(length = length(choices))
  consecutive_safe <- numeric(length = length(choices))
  
  # Initialize counters for risky and safe choices
  count_risky <- 0
  count_safe <- 0
  
  # Loop through choices to calculate consecutive counts
  for (i in 1:length(choices)) {
    # Reset counters if current choice is NA
    if (is.na(choices[i])) {
      count_risky <- 0
      count_safe <- 0
      consecutive_risky[i] <- count_risky
      consecutive_safe[i] <- count_safe
      next
    }
    
    # Increment counters based on current choice and whether it matches the previous choice
    if (i == 1 || is.na(choices[i-1])) {  # Handle the first element or immediately after an NA
      count_risky <- ifelse(choices[i] == 1, 1, 0)
      count_safe <- ifelse(choices[i] == 0, 1, 0)
    } else {
      if (choices[i] == 1) {
        count_risky <- ifelse(choices[i-1] == 1, count_risky + 1, 1)
        count_safe <- 0
      } else {  # Implicitly choices[i] == 0
        count_safe <- ifelse(choices[i-1] == 0, count_safe + 1, 1)
        count_risky <- 0
      }
    }
    
    # Assign the calculated counts to the respective vectors
    consecutive_risky[i] <- count_risky
    consecutive_safe[i] <- count_safe
  }
  
  return(list(risky = consecutive_risky, safe = consecutive_safe))
}

# Function that calculates the proportion of risky choices in a rolling window of 5 observations (total for market is 30 observations)
calculate_rolling_proportion <- function(choices) {
  rollapply(choices, width = 5, FUN = function(x) mean(x, na.rm = TRUE), partial = TRUE, align = 'right')
}

# Assuming your data is in a data frame called data
# Initialize an empty list to store player-specific data frames
player_data_list <- list()

for(player_id in unique(data$player.id)) {
  player_data <- data %>%
    filter(player.id == player_id) %>%
    arrange(period) %>%
    mutate(
      period = row_number(),
      price_change = ifelse(lag(player.shares_result) == 0 & player.shares_result > 0, 1,
                            (player.shares_result / lag(player.shares_result) - 1)),
      Cumulative_Risk = cumsum(player.risk),
      Risk_Change = c(NA, diff(player.risk)),
      Cumulative_Cash_Result = cumsum(player.cash_result),
      No_Shares = player.shares_result,
      Shares_Percent_Change = ifelse(lag(player.shares_result) == 0 & player.shares_result > 0, 100,
                                     (player.shares_result / lag(player.shares_result) - 1) * 100),
      Moving_Average_Risk = zoo::rollapply(player.risk, width = 5, FUN = mean, fill = NA, align = "right"),
      Rolling_Proportion_Risky = calculate_rolling_proportion(player.risk)
    ) %>%
    replace_na(list(Shares_Percent_Change = 0)) # Replace NA (including where previous period's shares were 0) with 0
  
  # Calculate consecutive choices outside the mutate to avoid nesting issues
  consecutive_choices <- calculate_consecutive_choices(player_data$player.risk)
  player_data$consecutive_risky <- consecutive_choices$risky
  player_data$consecutive_safe <- consecutive_choices$safe
  
  player_data_list[[as.character(player_id)]] <- player_data
}

# At this point, player_data_list contains a data frame for each player

# Assuming you want to plot for the first player in the list
player_data <- player_data_list[[1]] # Adjust the index for different players

plot <- ggplot(player_data, aes(x = period, y = price_change)) +
  geom_line() + # Use geom_line() to connect the points through periods
  geom_point() + # Use geom_point() to mark each period's value
  labs(title = "Price dynamics", y = "Price change (%)", x = "Period") +
  theme_minimal()

print(plot)


# Combine all individual player data frames into one for market-wide analysis
market_data <- do.call(rbind, player_data_list)

# Calculate market-wide averages
market_averages <- market_data %>%
  group_by(period) %>%
  summarise(
    Average_Risk = mean(player.risk, na.rm = TRUE),
    Average_Cumulative_Risk = mean(Cumulative_Risk, na.rm = TRUE),
    Average_Risk_Change = mean(Risk_Change, na.rm = TRUE),
    Average_Cumulative_Cash_Result = mean(Cumulative_Cash_Result, na.rm = TRUE),
    Average_No_Shares = mean(No_Shares, na.rm = TRUE) # Using No_Shares as it's directly from the mutated data
  )

# Function to calculate averages for sub-periods
calculate_sub_period_averages <- function(data, start_period, end_period) {
  data %>%
    filter(period >= start_period, period <= end_period) %>%
    summarise(
      Average_Risk = mean(player.risk, na.rm = TRUE),
      Average_Cumulative_Risk = mean(Cumulative_Risk, na.rm = TRUE),
      Average_Risk_Change = mean(Risk_Change, na.rm = TRUE),
      Average_Cumulative_Cash_Result = mean(Cumulative_Cash_Result, na.rm = TRUE),
      Average_No_Shares = mean(No_Shares, na.rm = TRUE)
    )
}

sub_period_1 <- calculate_sub_period_averages(market_data, 1, 10)
sub_period_2 <- calculate_sub_period_averages(market_data, 11, 20)
sub_period_3 <- calculate_sub_period_averages(market_data, 21, 30)

# Now you have market_averages, sub_period_1, sub_period_2, and sub_period_3 with the required averages

# Add ln_price changes in data
data <- data %>%
  arrange(player.id, period) %>%
  group_by(player.id) %>% # Assuming price change calculation is relevant within each player's data
  mutate(
    price_change = (group.price / lag(group.price) - 1)
  ) %>%
  ungroup() # Remove grouping if no longer needed

# Replace NA in the first period's price_change with 0 or appropriate value
data$price_change[is.na(data$price_change)] <- 0


# Calculate individual-level correlations
individual_correlations <- data %>%
  group_by(player.id) %>%
  summarise(
    Correlation_Risk_PriceChange = cor(player.risk, price_change, use = "complete.obs") # change player.risk with other risk-related variables
  )

# View the results
print(individual_correlations)


### plot consecutive risk and market price
library(ggplot2)
library(dplyr)
library(tidyr)

# Assuming player_data_list is your list of data frames for each participant
# First, add a participant identifier to each data frame
for(i in seq_along(player_data_list)) {
  player_data_list[[i]] <- player_data_list[[i]] %>%
    mutate(participant_id = as.character(i)) # Add participant ID
}

# Combine all participant data frames into one
combined_data <- bind_rows(player_data_list)

# Prepare the data for the first set of figures (consecutive risky and prices)
long_data_risky <- combined_data %>%
  pivot_longer(cols = c("consecutive_risky", "group.price"), names_to = "variable", values_to = "value")

# Prepare the data for the second set of figures (consecutive safe and prices)
long_data_safe <- combined_data %>%
  pivot_longer(cols = c("consecutive_safe", "group.price"), names_to = "variable", values_to = "value")


# Create the plot for risky choices
plot_risky <- ggplot(long_data_risky, aes(x = period, y = value, color = variable)) +
  geom_line(data = long_data_risky %>% filter(variable == "group.price")) +
  geom_point(data = long_data_risky %>% filter(variable == "consecutive_risky"), size=1) +
  facet_wrap(~ participant_id, nrow = 2, ncol = 3) +
  scale_colour_manual(values = c("consecutive_risky" = "blue", "Market price" = "red")) +
  labs(title = "Price and Consecutive Risky Choices Over Periods", x = "Period", y = "Value") +
  theme_minimal() +
  theme(legend.title = element_blank(), legend.position = "bottom",
        panel.background = element_rect(fill = "white", colour = NA), # Ensure panel background is white
        plot.background = element_rect(fill = "white", colour = NA)) # Ensure plot background is white

# Save the plot
print(plot_risky)
ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/figures/risk/individual_consecutive_risk_choices.png", plot_risky, width = 12, height = 8, dpi = 300)

# Create the plot for safe choices
plot_safe <- ggplot(long_data_safe, aes(x = period, y = value, color = variable)) +
  geom_line(data = long_data_safe %>% filter(variable == "group.price")) +
  geom_point(data = long_data_safe %>% filter(variable == "consecutive_safe"), size=1) +
  facet_wrap(~ participant_id, nrow = 2, ncol = 3) +
  scale_colour_manual(values = c("consecutive_safe" = "blue", "Market price" = "red")) +
  labs(title = "Price and Consecutive Safe Choices Over Periods", x = "Period", y = "Value") +
  theme_minimal() +
  theme(legend.title = element_blank(), legend.position = "bottom",
        panel.background = element_rect(fill = "white", colour = NA), # Ensure panel background is white
        plot.background = element_rect(fill = "white", colour = NA)) # Ensure plot background is white

# Save the plot
print(plot_safe)
ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/figures/risk/individual_consecutive_safe_choices.png", plot_safe, width = 12, height = 8, dpi = 300)

# Add a new variable for the difference between consecutive_risky and consecutive_safe
combined_data <- combined_data %>%
  mutate(risky_safe_diff = consecutive_risky - consecutive_safe)

# Prepare the data for plotting the difference alongside price
long_data_diff <- combined_data %>%
  pivot_longer(cols = c("risky_safe_diff", "group.price"), names_to = "variable", values_to = "value")

plot_risky_safe_diff <- ggplot(long_data_diff, aes(x = period, y = value, color = variable)) +
  geom_line(data = long_data_diff %>% filter(variable == "group.price"), aes(color = "Price")) +
  geom_line(data = long_data_diff %>% filter(variable == "risky_safe_diff"), aes(color = "Risky-Safe Difference")) + # Line for risky_safe_diff
  geom_point(data = long_data_diff %>% filter(variable == "risky_safe_diff"), aes(color = "Risky-Safe Difference"), size = 1) + # Points on the line
  facet_wrap(~ participant_id, nrow = 2, ncol = 3) +
  scale_colour_manual(values = c("Risky-Safe Difference" = "blue", "Price" = "red")) +
  labs(title = "Price and Risky-Safe Difference Over Periods", x = "Period", y = "Value") +
  theme_minimal() +
  theme(legend.title = element_blank(), legend.position = "bottom",
        panel.background = element_rect(fill = "white", colour = NA), # Ensure panel background is white
        plot.background = element_rect(fill = "white", colour = NA)) # Ensure plot background is white

# Save the plot to a PNG file
print(plot_risky_safe_diff)
ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/figures/risk/individual_consecutive_risky_safe_diff.png", plot_risky_safe_diff, width = 12, height = 8, dpi = 300)


### Plotting individual moving average risk
# Prepare the data for Moving Average Risk
long_data_moving_average_risk <- combined_data %>%
  pivot_longer(cols = c("Moving_Average_Risk", "group.price"), names_to = "variable", values_to = "value")

plot_moving_average_risk <- ggplot(long_data_moving_average_risk, aes(x = period, y = value, color = variable)) +
  geom_line(data = long_data_moving_average_risk %>% filter(variable == "group.price")) +
  geom_point(data = long_data_moving_average_risk %>% filter(variable == "Moving_Average_Risk"), size=1) +
  facet_wrap(~ participant_id, nrow = 2, ncol = 3) +
  scale_colour_manual(values = c("Moving_Average_Risk" = "blue", "group.price" = "black")) +
  labs(title = "Price and Moving Average Risk Over Periods", x = "Period", y = "Value") +
  theme_minimal() +
  theme(legend.title = element_blank(), legend.position = "bottom",
        panel.background = element_rect(fill = "white", colour = NA), # Ensure panel background is white
        plot.background = element_rect(fill = "white", colour = NA)) # Ensure plot background is white

plot_moving_average_risk
# Save the plot
ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/figures/risk/individual_moving_average_risk.png", plot_moving_average_risk, width = 12, height = 8, dpi = 300)


# Prepare the data for Rolling Proportion Risky
long_data_rolling_proportion_risky <- combined_data %>%
  pivot_longer(cols = c("Rolling_Proportion_Risky", "group.price"), names_to = "variable", values_to = "value")

plot_rolling_proportion_risky <- ggplot(long_data_rolling_proportion_risky, aes(x = period, y = value, color = variable)) +
  geom_line(data = long_data_rolling_proportion_risky %>% filter(variable == "group.price")) +
  geom_point(data = long_data_rolling_proportion_risky %>% filter(variable == "Rolling_Proportion_Risky"), size=1) +
  facet_wrap(~ participant_id, nrow = 2, ncol = 3) +
  scale_colour_manual(values = c("Rolling_Proportion_Risky" = "blue", "group.price" = "black")) +
  labs(title = "Price and Rolling Proportion Risky Over Periods", x = "Period", y = "Value") +
  theme_minimal() +
  theme(legend.position = "bottom")

plot_rolling_proportion_risky
# Save the plot
ggsave("plot_rolling_proportion_risky.png", plot_rolling_proportion_risky, width = 12, height = 8, dpi = 300)


### Market data across participants (averages for all subjects per each period)
# Calculate the averages for consecutive_risky, consecutive_safe, and risky_safe_diff for each period
market_data <- combined_data %>%
  group_by(period) %>%
  summarise(
    avg_consecutive_risky = mean(consecutive_risky, na.rm = TRUE),
    avg_consecutive_safe = mean(consecutive_safe, na.rm = TRUE),
    avg_risky_safe_diff = mean(risky_safe_diff, na.rm = TRUE),
    # avg_price = mean(group.price, na.rm = TRUE) # Assuming the price column is named 'price'
  ) %>%
  pivot_longer(cols = starts_with("avg"), names_to = "variable", values_to = "value")

# Since the variable column includes prefixes, let's clean it up for better legend labels in the plot
market_data$variable <- sub("avg_", "", market_data$variable)

# Price data
price_data <- data %>%
  #filter(price == "price") %>%
  arrange(period) %>%
  slice(1:33) %>%
  select(period, price_change, group.price)

price_data <- price_data %>%
  slice(4:33) %>%
  mutate(period = row_number())

# Add price_data to market_data
# Prepare price_data to match the format of market_data
price_data_formatted <- price_data %>%
  mutate(variable = "price",  # Add a 'variable' column for merging
         value = group.price) %>%  # Use 'group.price' as the value to plot
  select(period, variable, value)

# Ensure that 'period' in price_data_formatted starts from 1 to match market_data after slicing
price_data_formatted$period <- seq_along(price_data_formatted$period)

# Combine market_data with the formatted price data
market_data_combined <- bind_rows(market_data, price_data_formatted)



# Filter out the unnecessary rows first, if any exist beyond period 30
market_data_combined_filtered <- market_data_combined %>%
  filter(period <= 30)

# Pivot the data from long to wide format
market_combined <- market_data_combined_filtered %>%
  pivot_wider(names_from = variable, values_from = value) %>%
  select(period, consecutive_risky, consecutive_safe, risky_safe_diff)

# Ensure the 'period' runs from 1 to 30 after filtering
market_combined <- market_combined %>%
  mutate(period = row_number())

# Plot the market behavior
market_plot <- ggplot(market_data_combined_filtered, aes(x = period, y = value, color = variable)) +
  geom_line() +
  geom_point(aes(shape = variable), size = 2) +  # Use shapes to differentiate variables
  scale_color_manual(values = c("consecutive_risky" = "blue", 
                                "consecutive_safe" = "green",
                                "risky_safe_diff" = "purple",
                                "price" = "red")) +  # 'price' now explicitly included
  labs(title = "Market Behavior: Averages of Risky, Safe Choices, and Price", 
       x = "Period", 
       y = "Average Value") +
  theme_minimal() +
  theme(legend.title = element_blank(), legend.position = "bottom",
        panel.background = element_rect(fill = "white", colour = NA), # Ensure panel background is white
        plot.background = element_rect(fill = "white", colour = NA)) # Ensure plot background is white

# Display the plot
print(market_plot)
# Save the plot to a PNG file
ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/figures/risk/market_behavior_risk_plot.png", market_plot, width = 12, height = 8, dpi = 300)


### Only consecutive risky and safe difference
# Filter to include only 'consecutive_risky' and 'price'
filtered_data <- market_data_combined %>%
  filter(variable %in% c("consecutive_risky", "price"))
filtered_data <- filtered_data %>%
  slice(-1:-3)  # Removes the first three rows
filtered_data <- filtered_data %>%
  mutate(period = ifelse(row_number() <= 30, row_number(), period))  # Adjust 'period' only for the first 30 rows

# Plot the filtered market behavior focusing on 'consecutive_risky' and 'price'
market_plot_consecutive_risky <- ggplot(filtered_data, aes(x = period, y = value, color = variable)) +
  geom_line() +
  geom_point(aes(shape = variable), size = 2) +  # Use shapes to differentiate variables
  scale_color_manual(values = c("consecutive_risky" = "blue", "price" = "red")) +  # Include only 'consecutive_risky' and 'price'
  labs(title = "Market Behavior: Consecutive Risky Choices and Price", 
       x = "Period", 
       y = "Value") +
  theme_minimal() +
  theme(legend.title = element_blank(), legend.position = "bottom",
        panel.background = element_rect(fill = "white", colour = NA), # Ensure panel background is white
        plot.background = element_rect(fill = "white", colour = NA)) # Ensure plot background is white

# Display the plot
print(market_plot_consecutive_risky)

# Save the plot to a PNG file
ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/figures/risk/market_behavior_consecutive_risky_plot.png", market_plot_consecutive_risky, width = 12, height = 8, dpi = 300)

# Filter to include only 'consecutive_safe' and 'price'
filtered_data <- market_data_combined %>%
  filter(variable %in% c("consecutive_safe", "price"))
filtered_data <- filtered_data %>%
  slice(-1:-3)  # Removes the first three rows
filtered_data <- filtered_data %>%
  mutate(period = ifelse(row_number() <= 30, row_number(), period))  # Adjust 'period' only for the first 30 rows

# Plot the filtered market behavior focusing on 'consecutive_risky' and 'price'
market_plot_consecutive_safe <- ggplot(filtered_data, aes(x = period, y = value, color = variable)) +
  geom_line() +
  geom_point(aes(shape = variable), size = 2) +  # Use shapes to differentiate variables
  scale_color_manual(values = c("consecutive_safe" = "blue", "price" = "red")) +  # Include only 'consecutive_risky' and 'price'
  labs(title = "Market Behavior: Consecutive Safe Choices and Price", 
       x = "Period", 
       y = "Value") +
  theme_minimal() +
  theme(legend.title = element_blank(), legend.position = "bottom",
        panel.background = element_rect(fill = "white", colour = NA), # Ensure panel background is white
        plot.background = element_rect(fill = "white", colour = NA)) # Ensure plot background is white

# Display the plot
plot(market_plot_consecutive_safe)

# Save the plot to a PNG file
ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/figures/risk/market_behavior_consecutive_safe_plot.png", market_plot_consecutive_safe, width = 12, height = 8, dpi = 300)



# Filter to include only 'risky_safe_diff' and 'price'
filtered_data <- market_data_combined %>%
  filter(variable %in% c("risky_safe_diff", "price"))
filtered_data <- filtered_data %>%
  slice(-1:-3)  # Removes the first three rows
filtered_data <- filtered_data %>%
  mutate(period = ifelse(row_number() <= 30, row_number(), period))  # Adjust 'period' only for the first 30 rows

# Plot the filtered market behavior focusing on 'consecutive_risky' and 'price'
market_plot_risky_safe_diff <- ggplot(filtered_data, aes(x = period, y = value, color = variable)) +
  geom_line() +
  geom_point(aes(shape = variable), size = 2) +  # Use shapes to differentiate variables
  scale_color_manual(values = c("risky_safe_diff" = "blue", "price" = "red")) +  # Include only 'consecutive_risky' and 'price'
  labs(title = "Market Behavior: Risky-Safe Difference Choices and Price", 
       x = "Period", 
       y = "Value") +
  theme_minimal() +
  theme(legend.title = element_blank(), legend.position = "bottom",
        panel.background = element_rect(fill = "white", colour = NA), # Ensure panel background is white
        plot.background = element_rect(fill = "white", colour = NA)) # Ensure plot background is white

# Display the plot
print(market_plot_risky_safe_diff)

# Save the plot to a PNG file
ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/figures/risk/market_behavior_risky_safe_diff_plot.png", market_plot_risky_safe_diff, width = 12, height = 8, dpi = 300)



######## corelate with Empatica data
# Aggregate EDA by participant and period
eda_data <- read_excel('/Users/mihai/Desktop/Caltech/Neurofinance/data/empatica/data_analysis/_all_subjects_EDA_statistics.xlsx') # Pilot 3 Empatica data EDA

# Assuming 'eda_data' contains your described structure
averaged_data <- eda_data %>%
  group_by(period) %>%
  summarise(
    avg_order_submission = mean(order_submission, na.rm = TRUE),
    avg_forecast_price = mean(forecast_price, na.rm = TRUE),
    avg_round_results = mean(round_results, na.rm = TRUE),
    avg_risk_elicitation = mean(risk_elicitation, na.rm = TRUE)
  )

# View the resulting averaged data
print(averaged_data) #order_submission	forecast_price	round_results	risk_elicitation

# Filter for consecutive_risky values only
consecutive_risky_data <- market_data %>%
  filter(variable == "consecutive_risky")

consecutive_safe_data <- market_data %>%
  filter(variable == "consecutive_safe")

risky_safe_diff_data <- market_data %>%
  filter(variable == "risky_safe_diff")

# Assuming market_data contains columns: period, risky_choices, consecutive_risky, consecutive_safe, risky_diff
# Join the averaged biometric data with the market data
# Join averaged_data with consecutive_risky_data
combined_data <- inner_join(averaged_data, consecutive_risky_data, by = "period")

# Join the result with consecutive_safe_data
combined_data <- inner_join(combined_data, consecutive_safe_data, by = "period")

# Finally, join the result with risky_safe_diff_data
combined_data <- inner_join(combined_data, risky_safe_diff_data, by = "period")

combined_data <- combined_data %>%
  rename(
    consecutive_risky = value.x,
    consecutive_safe = value.y,
    risky_safe_diff = value
  )

# Example: Plotting avg_order_submission against consecutive_risky
risky_eda<-ggplot(combined_data, aes(x = avg_round_results, y = consecutive_risky)) +
  geom_point() +
  geom_smooth(method = "lm") +  # Adding a linear trend line
  labs(title = "Avg Round Results vs. Consecutive Risky Choices",
       x = "Average Round Results", y = "Consecutive Risky Choices") +
  theme_minimal() +
  theme(legend.title = element_blank(), legend.position = "bottom",
      panel.background = element_rect(fill = "white", colour = NA), # Ensure panel background is white
      plot.background = element_rect(fill = "white", colour = NA)) # Ensure plot background is white
  
plot(risky_eda)
ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/figures/risk/avg_round_results_vs_consecutive_risky.png", risky_eda, width = 12, height = 8, dpi = 300)

# safe
safe_eda<-ggplot(combined_data, aes(x = avg_round_results, y = consecutive_safe)) +
  geom_point() +
  geom_smooth(method = "lm") +  # Adding a linear trend line
  labs(title = "Avg Round Results vs. Consecutive Safe Choices",
       x = "Average Round Results", y = "Consecutive Safe Choices") +
  theme_minimal() +
  theme(legend.title = element_blank(), legend.position = "bottom",
      panel.background = element_rect(fill = "white", colour = NA), # Ensure panel background is white
      plot.background = element_rect(fill = "white", colour = NA)) # Ensure plot background is white

plot(safe_eda)
ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/figures/risk/avg_round_results_vs_consecutive_safe.png", safe_eda, width = 12, height = 8, dpi = 300)

# safe
risky_safe_diff_eda<-ggplot(combined_data, aes(x = avg_order_submission, y = risky_safe_diff)) +
  geom_point() +
  geom_smooth(method = "lm") +  # Adding a linear trend line
  labs(title = "Avg Order Submission vs. Consecutive Risky-Safe Diff Choices",
       x = "Average Order Submission", y = "Consecutive Risky-Safe Diff Choices") +
  theme_minimal() +
  theme(legend.title = element_blank(), legend.position = "bottom",
      panel.background = element_rect(fill = "white", colour = NA), # Ensure panel background is white
      plot.background = element_rect(fill = "white", colour = NA)) # Ensure plot background is white

plot(risky_safe_diff_eda)
ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/figures/risk/avg_order_submission_vs_consecutive_risky_safe_diff.png", risky_safe_diff_eda, width = 12, height = 8, dpi = 300)


# Linear model for avg_order_submission vs risky_safe_diff
lm_model_diff <- lm(risky_safe_diff ~ avg_round_results, data = combined_data)
lm_model_risky <- lm(consecutive_risky ~ avg_order_submission, data = combined_data)
lm_model_safe <- lm(consecutive_safe ~ avg_order_submission, data = combined_data)

# Summary of the model to get statistics
summary(lm_model_risky)
summary(lm_model_safe)
summary(lm_model_diff)

### Now regression with price/price change variable variable
# First place price variable in combined data:
price_data <- data %>%
  #filter(price == "price") %>%
  arrange(period) %>%
  slice(1:33) %>%
  select(period, price_change, group.price)

price_data <- price_data %>%
  slice(4:33) %>%
  mutate(period = row_number())

## Add price and price_change to combined data to perform analysis
combined_data <- inner_join(combined_data, price_data)


# Linear model for price_pct_change vs consecutive_risky/consecutive_safe and risky_safe_diff (empatica e4 variables)
price_lm_model_risky <- lm(risky_safe_diff ~ price_change, data = combined_data)
price_lm_model_safe <- lm(consecutive_risky ~ price_change, data = combined_data)
price_lm_model_diff <- lm(consecutive_safe ~ price_change, data = combined_data)

# Summary of the model
summary(price_lm_model_risky)
summary(price_lm_model_safe)
summary(price_lm_model_diff)

### Price change and EDA
# price change and average price submission
price_change_order_submission_eda<-ggplot(combined_data, aes(x = avg_order_submission, y = price_change)) +
  geom_point() +
  geom_smooth(method = "lm") +  # Adding a linear trend line
  labs(title = "Avg Order Submission vs. Price change",
       x = "Average Order Submission", y = "Price change") +
  theme_minimal() +
  theme(legend.title = element_blank(), legend.position = "bottom",
        panel.background = element_rect(fill = "white", colour = NA), # Ensure panel background is white
        plot.background = element_rect(fill = "white", colour = NA)) # Ensure plot background is white

plot(price_change_order_submission_eda)
ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/figures/risk/price_change_vs_order_submission_eda.png", price_change_order_submission_eda, width = 12, height = 8, dpi = 300)


# price change and forecast page
price_change_forecast_price_eda<-ggplot(combined_data, aes(x = avg_forecast_price, y = price_change)) +
  geom_point() +
  geom_smooth(method = "lm") +  # Adding a linear trend line
  labs(title = "Avg Forecast Price vs. Price change",
       x = "Average Forecast Price", y = "Price change") +
  theme_minimal() +
  theme(legend.title = element_blank(), legend.position = "bottom",
        panel.background = element_rect(fill = "white", colour = NA), # Ensure panel background is white
        plot.background = element_rect(fill = "white", colour = NA)) # Ensure plot background is white

plot(price_change_forecast_price_eda)
ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/figures/risk/avg_price_change_vs_forecast_price.png", price_change_forecast_price_eda, width = 12, height = 8, dpi = 300)


# price change and round results
price_change_round_results_eda<-ggplot(combined_data, aes(x = avg_round_results, y = price_change)) +
  geom_point() +
  geom_smooth(method = "lm") +  # Adding a linear trend line
  labs(title = "Avg Round Results vs. Price change",
       x = "Average Round Results", y = "Price change") +
  theme_minimal() +
  theme(legend.title = element_blank(), legend.position = "bottom",
        panel.background = element_rect(fill = "white", colour = NA), # Ensure panel background is white
        plot.background = element_rect(fill = "white", colour = NA)) # Ensure plot background is white

plot(price_change_round_results_eda)
ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/figures/risk/avg_price_change_vs_round_results_eda.png", price_change_round_results_eda, width = 12, height = 8, dpi = 300)



# price change and risk elicitation
price_change_risk_elictation_eda<-ggplot(combined_data, aes(x = avg_risk_elicitation, y = price_change)) +
  geom_point() +
  geom_smooth(method = "lm") +  # Adding a linear trend line
  labs(title = "Avg Risk Elicitation vs. Price change",
       x = "Average Risk Elicitation", y = "Price change") +
  theme_minimal() +
  theme(legend.title = element_blank(), legend.position = "bottom",
        panel.background = element_rect(fill = "white", colour = NA), # Ensure panel background is white
        plot.background = element_rect(fill = "white", colour = NA)) # Ensure plot background is white

plot(price_change_risk_elictation_eda)
ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/figures/risk/avg_risk_elicitation_vs_price_change.png", price_change_risk_elictation_eda, width = 12, height = 8, dpi = 300)


