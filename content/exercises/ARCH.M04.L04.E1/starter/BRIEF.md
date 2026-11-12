# Brief: short links with click counts

From the product manager:

> Marketing wants their own link shortener. Anyone on the marketing team can create a short link for a long URL
> (optionally with a custom alias like `/spring-sale`). Visiting the short link redirects to the long URL. Marketing
> wants to see how many clicks each link got per day. Some links should stop working after a campaign ends.

Numbers from marketing (L01 used them):

- About 200,000 links created per day (campaign tools create them in bulk).
- About 50 clicks per link per day on average; peaks are about 8x the average.
- Click counts may be a few minutes behind. Redirects must be fast (p99 under 50 ms at the server).
- Keep links and daily counts for 2 years.
