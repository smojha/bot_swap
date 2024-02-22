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
library(reshape2)

rm(list=ls())

# Load the data
# Pilot 5
data <- read_csv('/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_2024_02_20_online/rounds_2024-02-20.csv') # Pilot 5 online

#data <- read_excel('/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_03_23_11_30/rounds_2023-11-30_forecast.xlsx', sheet = 'clean') # Pilot 3
# Prolific participants for pilot3 : 86T si 04R
# subject1 = 14L, rest are subject2, 3, 4

#import orders 
data_orders <- read_csv('/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_2024_02_20_online/orders_2024-02-20.csv') # Pilot 3
#data_orders <- read_excel('/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_03_23_11_30/orders_2023-11-30.xlsx') # Pilot 3

data_orders <- data_orders %>%
  rename(period = round_number)
data <- data %>%
  rename(period = subsession.round_number)

# Now extract price_data with price_change included
price_data <- data %>%
  select(period, group.price) # Now includes price_change

# 1. Average forward forecasts curve
forward_curve <- data %>%
  mutate(period_range = case_when(
    period <= 10 ~ "1-10",
    period <= 20 ~ "11-20",
    TRUE ~ "21-30"
  )) %>%
  group_by(period_range) %>%
  summarise(
    avg_f0 = mean(player.f0, na.rm = TRUE),
    avg_f1 = mean(player.f1, na.rm = TRUE),
    avg_f2 = mean(player.f2, na.rm = TRUE),
    avg_f3 = mean(player.f3, na.rm = TRUE)
  )

# 2. Deviation from Bids and Asks
# Calculate average bid and ask prices per period
average_prices <- data_orders %>%
  group_by(period, type) %>%
  summarise(
    avg_price = mean(price, na.rm = TRUE),
    .groups = 'drop'
  )

# Join this with your forecast data to calculate deviations
# Calculate average bid and ask prices per period separately
average_bid_prices <- data_orders %>%
  filter(type == "BUY") %>%
  group_by(period) %>%
  summarise(avg_bid_price = mean(price, na.rm = TRUE), .groups = 'drop')

average_ask_prices <- data_orders %>%
  filter(type == "SELL") %>%
  group_by(period) %>%
  summarise(avg_ask_price = mean(price, na.rm = TRUE), .groups = 'drop')

average_forecast_curve <- data %>%
  group_by(period) %>%
  summarise(
    avg_f0 = mean(player.f0, na.rm = TRUE),
    avg_f1 = mean(player.f1, na.rm = TRUE),
    avg_f2 = mean(player.f2, na.rm = TRUE),
    avg_f3 = mean(player.f3, na.rm = TRUE),
    .groups = 'drop'  # This option drops the grouping structure after summarising
  ) %>%
  slice(4:33) %>%  # Keep only rows 3 through 33
  mutate(period = row_number())
  
average_forecast_curve <- average_forecast_curve %>%
  mutate(
    avg_f1 = lag(avg_f1, n = 2, default = NA), # Shift avg_f1 starting from row 2
    avg_f2 = lag(avg_f2, n = 5, default = NA), # Shift avg_f2 starting from row 5
    avg_f3 = lag(avg_f3, n = 10, default = NA)  # Shift avg_f3 starting from row 10
  )

# Joining bid prices with forecast data (adjust similarly for asks if needed)
deviations_bid <- average_forecast_curve %>%
  left_join(average_bid_prices, by = "period") %>%
  mutate(
    deviation_f0_bid = avg_bid_price - avg_f0,
    deviation_f1_bid = avg_bid_price - avg_f1,
    deviation_f2_bid = avg_bid_price - avg_f2,
    deviation_f3_bid = avg_bid_price - avg_f3
  ) %>%
  mutate(period = row_number())

# Apply linear interpolation to fill missing values to bid deviations
deviations_bid <- deviations_bid %>%
  mutate(across(starts_with("deviation_f"), ~ na.approx(.x, na.rm = FALSE)),
         across(starts_with("avg_bid"), ~ na.approx(.x, na.rm = FALSE)))

# Assuming 'average_forecast_curve' contains the average forecasts for each period
deviations_ask <- average_forecast_curve %>%
  left_join(average_ask_prices, by = "period") %>%
  mutate(
    deviation_f0_ask = avg_ask_price - avg_f0,
    deviation_f1_ask = avg_ask_price - avg_f1, 
    deviation_f2_ask = avg_ask_price - avg_f2,
    deviation_f3_ask = avg_ask_price - avg_f3
  )%>%
  mutate(period = row_number())

# Apply linear interpolation to fill missing values to ask deviations
deviations_ask <- deviations_ask %>%
  mutate(across(starts_with("deviation_f"), ~ na.approx(.x, na.rm = FALSE)),
         across(starts_with("avg_ask"), ~ na.approx(.x, na.rm = FALSE)))

market_price <- data %>%
  group_by(period) %>%
  slice(1) %>%  # Keep only the first observation from each period
  ungroup() %>%  # Remove the grouping
  filter(period >= 4 & period <= 33) %>%  # Filter for periods 4 through 33
  select(period, group_price = group.price) %>%
  mutate(period = row_number())

# Join with deviations
deviations_bid <- deviations_bid %>%
  left_join(market_price, by = "period")

deviations_ask <- deviations_ask %>%
  left_join(market_price, by = "period")

# Plotting deviations for bids with group.price
bid_deviations <- ggplot(deviations_bid, aes(x = period)) +
  geom_line(aes(y = deviation_f0_bid, color = "Deviation of Forecast Period 0 from Bid"), size = 1) +
  geom_point(aes(y = deviation_f0_bid, color = "Deviation of Forecast Period 0 from Bid"), size = 1) +
  geom_line(aes(y = deviation_f1_bid, color = "Deviation of Forecast Period 2 from Bid"), size = 1) +
  geom_point(aes(y = deviation_f1_bid, color = "Deviation of Forecast Period 2 from Bid"), size = 1) +
  geom_line(aes(y = deviation_f2_bid, color = "Deviation of Forecast Period 5 from Bid"), size = 1) +
  geom_point(aes(y = deviation_f2_bid, color = "Deviation of Forecast Period 5 from Bid"), size = 1) +
  geom_line(aes(y = deviation_f3_bid, color = "Deviation of Forecast Period 10 from Bid"), size = 1) +
  geom_point(aes(y = deviation_f3_bid, color = "Deviation of Forecast Period 10 from Bid"), size = 1) +
  geom_line(aes(y = group_price, color = 'Market Price'), size = 1) +
  geom_point(aes(y = group_price, color = 'Market Price'), size = 1) +
  geom_hline(yintercept = 0, linetype = "dotted", color = "black") +  # Emphasize the 0 x-axis
  labs(title = "Bid Deviations and Market Price", x = "Period", y = "Deviation/Market Price", color = NULL) +  # Set color legend title to NULL
  scale_color_manual(values = c("Deviation of Forecast Period 0 from Bid" = "red", 
                                "Deviation of Forecast Period 2 from Bid" = "blue", 
                                "Deviation of Forecast Period 5 from Bid" = "green",
                                "Deviation of Forecast Period 10 from Bid" = "purple", 
                                "Market Price" = "black")) +
  theme_minimal() +
  theme(panel.background = element_rect(fill = "white", colour = "white"),
        plot.background = element_rect(fill = "white", colour = "white"),
        plot.title = element_text(size = 20),
        axis.title = element_text(size = 16),
        axis.text = element_text(size = 14),
        legend.title = element_blank(),  # Ensure the legend title is blank
        legend.text = element_text(size = 14),
        legend.position = "bottom") +
  guides(color = guide_legend(nrow = 2, byrow = TRUE, title = NULL))  # Ensure the legend title is set to NULL here too

# Display the plot
plot(bid_deviations)


# Save the plot to a PNG file
#ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/figures/forecast/deviation_from_avg_bid_to_market_price.png", bid_deviations, width = 12, height = 8, dpi = 300)
ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_2024_02_20_online/bid_deviations.png", bid_deviations, width = 10, height = 8)


# Plotting deviations for asks with group.price
ask_deviations <- ggplot(deviations_ask, aes(x = period)) +
  geom_line(aes(y = deviation_f0_ask, color = "Deviation of Forecast Period 0 from Ask"), size = 1) +
  geom_point(aes(y = deviation_f0_ask, color = "Deviation of Forecast Period 0 from Ask"), size = 1) +
  geom_line(aes(y = deviation_f1_ask, color = "Deviation of Forecast Period 2 from Ask"), size = 1) +
  geom_point(aes(y = deviation_f1_ask, color = "Deviation of Forecast Period 2 from Ask"), size = 1) +
  geom_line(aes(y = deviation_f2_ask, color = "Deviation of Forecast Period 5 from Ask"), size = 1) +
  geom_point(aes(y = deviation_f2_ask, color = "Deviation of Forecast Period 5 from Ask"), size = 1) +
  geom_line(aes(y = deviation_f3_ask, color = "Deviation of Forecast Period 10 from Ask"), size = 1) +
  geom_point(aes(y = deviation_f3_ask, color = "Deviation of Forecast Period 10 from Ask"), size = 1) +
  geom_line(aes(y = group_price, color = 'Market Price'), size = 1) +
  geom_point(aes(y = group_price, color = 'Market Price'), size = 1) +
  geom_hline(yintercept = 0, linetype = "dotted", color = "black") +  # Emphasize the 0 x-axis
  labs(title = "Ask Deviations and Market Price", x = "Period", y = "Deviation/Market Price", color = NULL) +  # Set color legend title to NULL
  scale_color_manual(values = c("Deviation of Forecast Period 0 from Ask" = "red", 
                                "Deviation of Forecast Period 2 from Ask" = "blue", 
                                "Deviation of Forecast Period 5 from Ask" = "green",
                                "Deviation of Forecast Period 10 from Ask" = "purple", 
                                "Market Price" = "black")) +
  theme_minimal() +
  theme(panel.background = element_rect(fill = "white", colour = "white"),
        plot.background = element_rect(fill = "white", colour = "white"),
        plot.title = element_text(size = 20),
        axis.title = element_text(size = 16),
        axis.text = element_text(size = 14),
        legend.title = element_blank(),  # Ensure the legend title is blank
        legend.text = element_text(size = 14),
        legend.position = "bottom") +
  guides(color = guide_legend(nrow = 2, byrow = TRUE, title = NULL))  # Ensure the legend title is set to NULL here too

plot(ask_deviations)

# Save the plot to a PNG file
#ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/figures/forecast/deviation_from_avg_ask_to_market_price.png", ask_deviations, width = 12, height = 8, dpi = 300)
ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_2024_02_20_online/ask_deviations.png", ask_deviations, width = 10, height = 8)


##### Average bid-ask deviation
# Calculate the average bid-ask spread per period
average_bid_ask_spread <- average_bid_prices %>%
  inner_join(average_ask_prices, by = "period", suffix = c("_bid", "_ask")) %>%
  mutate(avg_bid_ask_spread = avg_ask_price - avg_bid_price)

# Calculate Deviations for Average Bid-Ask Spread
deviations_bid_ask <- average_forecast_curve %>%
  left_join(average_bid_ask_spread %>% select(period, avg_bid_ask_spread), by = "period") %>%
  mutate(
    deviation_f0_bid_ask = avg_bid_ask_spread - avg_f0,
    deviation_f1_bid_ask = avg_bid_ask_spread - avg_f1,
    deviation_f2_bid_ask = avg_bid_ask_spread - avg_f2,
    deviation_f3_bid_ask = avg_bid_ask_spread - avg_f3,
  )

# Apply linear interpolation to fill missing values to bid-ask deviations
deviations_bid_ask <- deviations_bid_ask %>%
  mutate(across(starts_with("deviation_f"), ~ na.approx(.x, na.rm = FALSE)),
         across(starts_with("avg_bid_ask"), ~ na.approx(.x, na.rm = FALSE)))

deviations_bid_ask <- deviations_bid_ask %>%
  left_join(market_price, by = "period")

# Plotting deviations for the average bid-ask spread with group.price
bid_ask_deviations <- ggplot(deviations_bid_ask, aes(x = period)) +
  geom_line(aes(y = deviation_f0_bid_ask, color = "Deviation of Forecast Period 0 from Bid-Ask"), size = 1) +
  geom_point(aes(y = deviation_f0_bid_ask, color = "Deviation of Forecast Period 0 from Bid-Ask"), size = 1) +
  geom_line(aes(y = deviation_f1_bid_ask, color = "Deviation of Forecast Period 1 from Bid-Ask"), size = 1) +
  geom_point(aes(y = deviation_f1_bid_ask, color = "Deviation of Forecast Period 1 from Bid-Ask"), size = 1) +
  geom_line(aes(y = deviation_f2_bid_ask, color = "Deviation of Forecast Period 2 from Bid-Ask"), size = 1) +
  geom_point(aes(y = deviation_f2_bid_ask, color = "Deviation of Forecast Period 2 from Bid-Ask"), size = 1) +
  geom_line(aes(y = deviation_f3_bid_ask, color = "Deviation of Forecast Period 3 from Bid-Ask"), size = 1) +
  geom_point(aes(y = deviation_f3_bid_ask, color = "Deviation of Forecast Period 3 from Bid-Ask"), size = 1) +
  geom_line(aes(y = group_price, color = 'Market Price'), size = 1) +
  geom_point(aes(y = group_price, color = 'Market Price'), size = 1) +
  geom_hline(yintercept = 0, linetype = "dotted", color = "black") +  # Emphasize the 0 x-axis
  labs(title = "Bid-Ask Deviations and Market Price", x = "Period", y = "Deviation/Market Price", color = NULL) +  # Set color legend title to NULL
  scale_color_manual(values = c("Deviation of Forecast Period 0 from Bid-Ask" = "red", 
                                "Deviation of Forecast Period 1 from Bid-Ask" = "blue", 
                                "Deviation of Forecast Period 2 from Bid-Ask" = "green",
                                "Deviation of Forecast Period 3 from Bid-Ask" = "purple", 
                                "Market Price" = "black")) +
  theme_minimal() +
  theme(panel.background = element_rect(fill = "white", colour = "white"),
        plot.background = element_rect(fill = "white", colour = "white"),
        plot.title = element_text(size = 20),
        axis.title = element_text(size = 16),
        axis.text = element_text(size = 14),
        legend.title = element_blank(),  # Ensure the legend title is blank
        legend.text = element_text(size = 14),
        legend.position = "bottom") +
  guides(color = guide_legend(nrow = 2, byrow = TRUE, title = NULL))  # Ensure the legend title is set to NULL here too

plot(bid_ask_deviations)

#Save files:
ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/figures/forecast/deviation_from_avg_ask_to_market_price.png", bid_ask_deviations, width = 12, height = 8, dpi = 300)



#### 3. Average forecast curve
# Read the CSV file (replace 'forecast_data.xlsx' with actual file path)

forecast_data <- read_csv('/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_2024_02_20_online/rounds_2024-02-20.csv')

#forecast_data <- read_excel('/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_2024_01_12/rounds_2024-01-12_forecast.xlsx', sheet = 'forecast') # Pilot 4, online only
#forecast_data <- read_excel('/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_03_23_11_30/rounds_2023-11-30_forecast.xlsx', sheet = 'forecast') # Pilot 3
#forecast_data <- read_excel('/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_01_23_11_16/rounds_2023-11-16_forecast.xlsx', sheet = 'forecast') # Pilot 1

# Function to replace NA with row average or a non-NA value
replace_na_with_row_avg <- function(x) {
  if (all(is.na(x))) {
    return(x)
  }
  na_count <- sum(is.na(x))
  if (na_count > 0 && na_count < length(x)) {
    row_avg <- mean(x, na.rm = TRUE)
    x[is.na(x)] <- row_avg
  }
  return(x)
}

# Apply the function to your forecast_data
forecast_data <- forecast_data %>%
  mutate(across(starts_with("player.f"), replace_na_with_row_avg))

# Replace entirely empty rows with values from the previous round
forecast_data <- forecast_data %>%
  fill(starts_with("player.f"), .direction = "down")

# Create an empty 33x4 matrix for the forecast
forecast_matrix <- matrix(NA, nrow = 33, ncol = 4)
colnames(forecast_matrix) <- paste("Forecast for Period", 0:3)

# Calculate the averages and fill the matrix
for (round in 1:33) {
  start_row <- (round - 1) * 18 + 1 # 18 here because there are 18 participants, change accordingly
  end_row <- round * 18 # 18 here because there are 18 participants, change accordingly
  for (period in 1:4) {
    column_name <- paste("player.f", period - 1, sep = "")
    # Extract data as a numeric vector
    forecast_values <- as.numeric(forecast_data[[column_name]][start_row:end_row])
    # Calculate the mean, if the conversion was successful
    if (!all(is.na(forecast_values))) {
      forecast_matrix[round, period] <- mean(forecast_values, na.rm = TRUE)
    }
  }
}


# Check the forecast_matrix
forecast_matrix

# Drop first 3 rows
# Drop the first 3 rows from the original forecast_matrix
forecast_matrix_30 <- forecast_matrix[-c(1:3), ]

# Initialize a new matrix for shifted data
shifted_matrix <- matrix(NA, nrow = 30, ncol = 4)
colnames(shifted_matrix) <- paste("Forecast for Period", 0:3)

# Shift forecasts as specified

shifted_matrix[, 1] <- forecast_matrix_30[, 1] # No shift for Period 0 (column 1)
shifted_matrix[2:30, 2] <- forecast_matrix_30[1:29, 2] # Shift Period 1 (column 2) so that rows start from row 2, row 1 will be NA
shifted_matrix[5:30, 3] <- forecast_matrix_30[1:26, 3] # Shift Period 2 (column 3) so that rows start from row 5, rows 1-4 will be NA
shifted_matrix[10:30, 4] <- forecast_matrix_30[1:21, 4] # Shift Period 3 (column 4) so that rows start from row 10, rows 1-9 will be NA

## Add group.price to shifted_matrix from deviations
# Assuming 'deviations' contains a 'group.price' column with at least 30 observations
group_prices <- deviations_bid_ask$group_price[1:30]

# Add group.price to the shifted matrix as a new column
shifted_matrix <- cbind(shifted_matrix, group.price = group_prices)

# Convert to dataframe
forecast_df_shifted <- as.data.frame(shifted_matrix)
forecast_df_shifted$period <- 1:30 # add period as x-axis for figure in qqplot2
colnames(forecast_df_shifted) <- c("f0", "f1", "f2", "f3", "group.price", "period") # rename columns


# Plot the data
forecast_curve <- ggplot(forecast_df_shifted, aes(x = period)) +
  geom_line(aes(y = f0, color = "Forecast Period 0"), linetype = "dashed", size = 1.2) +
  geom_line(aes(y = f1, color = "Forecast Period 2"), linetype = "dashed", size = 1.2) +
  geom_line(aes(y = f2, color = "Forecast Period 5"), linetype = "dashed", size = 1.2) +
  geom_line(aes(y = f3, color = "Forecast Period 10"), linetype = "dashed", size = 1.2) +
  geom_line(aes(y = group.price, color = "Market Price"), linetype = "solid", size = 1.2) +
  geom_point(aes(y = group.price, color = "Market Price"), size = 1) +
  geom_hline(yintercept = 14, linetype = "dashed", color = "black", size = 1.2) +
  scale_color_manual(values = c("Forecast Period 0" = "red", 
                                "Forecast Period 2" = "blue", 
                                "Forecast Period 5" = "green",
                                "Forecast Period 10" = "purple",
                                "Market Price" = "black")) +
  labs(title = "Forecast and Market Price per Period", x = "Period", y = "Price", color = "Indicator") +
  theme_minimal() +
  theme(legend.title = element_blank(), legend.position = "bottom",
        panel.background = element_rect(fill = "white", colour = NA),
        plot.background = element_rect(fill = "white", colour = NA),
        legend.text = element_text(size = 14))

# Plot `forecast_curve` to visualize the changes.
plot(forecast_curve)

# save plots
#ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/figures/forecast/forecast_curve.png", forecast_curve, width = 10, height = 8)
ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_2024_02_20_online/forecast_curve.png", forecast_curve, width = 10, height = 8)

forecast_matrix_df = forecast_df_shifted

# Add new columns for the difference between price and each forecast
forecast_matrix_df$diff_f0 = forecast_matrix_df$group.price - forecast_matrix_df$f0
forecast_matrix_df$diff_f1 = forecast_matrix_df$group.price - forecast_matrix_df$f1
forecast_matrix_df$diff_f2 = forecast_matrix_df$group.price - forecast_matrix_df$f2
forecast_matrix_df$diff_f3 = forecast_matrix_df$group.price - forecast_matrix_df$f3

# Plotting the differences (surprise)
forecast_curve_surprise <- ggplot(forecast_matrix_df, aes(x = period)) +
  geom_line(aes(y = diff_f0, color = "Price - Forecast 0"), linetype = "dashed", size = 1.2) +
  geom_line(aes(y = diff_f1, color = "Price - Forecast 2"), linetype = "dashed", size = 1.2) +
  geom_line(aes(y = diff_f2, color = "Price - Forecast 5"), linetype = "dashed", size = 1.2) +
  geom_line(aes(y = diff_f3, color = "Price - Forecast 10"), linetype = "dashed", size = 1.2) +
  geom_line(aes(y = group.price, color = "Market Price"), linetype = "solid", size = 1.2) +
  geom_point(aes(y = group.price, color = "Market Price"), size = 1) +
  geom_hline(yintercept = 14, linetype = "dashed", color = "black", size = 1.2) +
  geom_blank(aes(color = "Fundamental Value")) +
  scale_color_manual(values = c("Price - Forecast 0" = "red", 
                                "Price - Forecast 2" = "blue", 
                                "Price - Forecast 5" = "green",
                                "Price - Forecast 10" = "purple",
                                "Market Price" = "black",
                                "Fundamental Value" = "black")) +
  labs(title = "Forecast Surprises and Market Price per Period", x = "Period", y = "Price Difference", color = "Indicator") +
  theme_minimal() +
  theme(legend.title = element_blank(), legend.position = "bottom",
        panel.background = element_rect(fill = "white", colour = NA),
        plot.background = element_rect(fill = "white", colour = NA),
        legend.text = element_text(size = 14)) # Increase the legend text size


# Display the plot
plot(forecast_curve_surprise)
#ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/figures/forecast/forecast_curve_surprise.png", forecast_curve_surprise, width = 10, height = 8, dpi=300)
ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_2024_02_20_online/forecast_curve_surprise.png", forecast_curve_surprise, width = 10, height = 8)

## Add analysis on empatica E4 data correlations and regressions
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

# Filter for different forecast periods
f0_deviation <- forecast_matrix_df$price - forecast_matrix_df$f0
f1_deviation <- forecast_matrix_df$price - forecast_matrix_df$f1
f2_deviation <- forecast_matrix_df$price - forecast_matrix_df$f2
f3_deviation <- forecast_matrix_df$price - forecast_matrix_df$f3

# Combine data to perform regressions
combined_data <- inner_join(averaged_data, forecast_matrix_df, by = "period")

# Example: Plotting avg_order_submission against consecutive_risky
ggplot(combined_data, aes(x = avg_forecast_price, y = f3_deviation)) +
  geom_point() +
  geom_smooth(method = "lm") +  # Adding a linear trend line
  labs(title = "Avg Order Submission E4 EDA vs. Forecast",
       x = "Average Order Submission E4 EDA", y = "Forecast") +
  theme_minimal()

# Save the plot
ggsave("avg_order_submission_e4_forecast_f0.png", width = 8, height = 6, dpi = 300) # ... change avg_order_sub / forecast_price / round_results / risk_elicitation vs forecast_f0 f1 f2 or f3

# Linear model for avg_order_submission vs forecasts:
lm_model_f0 <- lm(f0_deviation ~ avg_order_submission, data = combined_data)
lm_model_f1 <- lm(f1_deviation ~ avg_order_submission, data = combined_data)
lm_model_f2 <- lm(f2_deviation ~ avg_order_submission, data = combined_data)
lm_model_f3 <- lm(f3_deviation ~ avg_order_submission, data = combined_data)

# Summary of the model to get statistics
summary(lm_model_f0)
summary(lm_model_f1)
summary(lm_model_f2)
summary(lm_model_f3)


# Save files:
# Create a new workbook
wb <- createWorkbook()

# Add sheets with data for each variable
addWorksheet(wb, "average_forecast_curve")
writeData(wb, "average_forecast_curve", average_forecast_curve)

addWorksheet(wb, "average_bid_ask_spread")
writeData(wb, "average_bid_ask_spread", average_bid_ask_spread)

addWorksheet(wb, "deviations_bid")
writeData(wb, "deviations_bid", deviations_bid)

addWorksheet(wb, "deviations_ask")
writeData(wb, "deviations_ask", deviations_ask)

addWorksheet(wb, "deviations_bid_ask")
writeData(wb, "deviations_bid_ask", deviations_bid_ask)

addWorksheet(wb, "forecast_matrix_df")
writeData(wb, "forecast_matrix_df", forecast_matrix_df)

addWorksheet(wb, "combined_data")
writeData(wb, "combined_data", combined_data)

# Save the workbook to the specified location
saveWorkbook(wb, "/Users/mihai/Desktop/Caltech/Neurofinance/data/forecast_analysis.xlsx", overwrite = TRUE)


