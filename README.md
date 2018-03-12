Apache Log Simulator
====================
This script outputs realistic-looking Apache logs by simulating user browsing behavior, given a site structure as input.  User sessions begin at random times throughout the course of a week but use weighted probabilities slanted towards access during the weekday and during core business hours.

By default, these will be sent to standard out as they're generated, meaning the logs will be locally ordered by time within a particular user's session, but not globally ordered among all sessions.  However, specifying `-s` or `--sort` at run time will result in a temporary SQLite database being created and then read from in order to output the logs in chronological time.

History
=======
This script came out of a presentation by CTSC during an [engagement with Cal Poly Pomona](http://blog.trustedci.org/search/label/sfs), where we presented a workshop for cybersecurity students in the Scholarship for Service program.  In order to provide a realistic hands on exercise looking for potential indicators of compromise in logs, we first needed a way of generating a lot of logs that looked like normal user traffic.

Site Structure Configuration
============================
The configuration of the simulated website is specified in `pages.conf`, or in another file specified as an argument at runtime (using `-p <file>` or `--pages <file>`).  Links as well as included content (images, css, scripts) can be specified on a per-page basis or globally included on all pages.

At minimum, each page must be specified with a size.  No status is required for working pages.

    [/news.php]
    size = 583

Broken links that result in 404 errors are also supported and must be specified.  Specifying a size for these is option.  Without a size, the script will use a default value from `settings.conf`.  Below is an example of configuration for a missing page:

    [/agenda.php]
    status = 404

Tunable Parameters
==================
The script has a number of parameters that can be tuned in `settings.conf`, or in another file specified as an argument at runtime (using `-c <file>` or `--config <file>`).  These include both probability weights and settings.

Settings include, among other options:
 * Starting date and timezone
 * Lists of user agents
 * Lists of referers
 * Default sizes for included content (images, css, scripts)
 * Default size for 404 responses

Probabilities include, among other options:
 * Odds of a user "clicking" another link after browsing a page successfully
 * Odds of a user coming directly to the site, versus using a referer
 * Values for which hours and which days should be represented most frequently
 * Values for which referers and user agents are most common

Sample Output
=============
Below is a sample of log entries for one particular "browsing session" produced using the example pages.conf and settings.conf included in the GitHub repository.  **Please note** that IP addresses are generated randomly from within the script and not based on real information.  Any relation to activity in the real world is purely coincidental.

    201.4.67.130 - - [22/Mar/2017:09:47:55 -0500] "GET /chemistry.php HTTP/1.1" 200 2341 "https://www.google.com/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36"
    201.4.67.130 - - [22/Mar/2017:09:47:55 -0500] "GET /style/science.css HTTP/1.1" 200 520 "http://www.example.com/chemistry.php" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36"
    201.4.67.130 - - [22/Mar/2017:09:47:55 -0500] "GET /style/main.css HTTP/1.1" 200 341 "http://www.example.com/chemistry.php" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36"
    201.4.67.130 - - [22/Mar/2017:09:47:55 -0500] "GET /images/header_bg.jpg HTTP/1.1" 200 725 "http://www.example.com/chemistry.php" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36"
    201.4.67.130 - - [22/Mar/2017:09:49:04 -0500] "GET /resources.php HTTP/1.1" 200 5839 "http://www.example.com/chemistry.php" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36"
    201.4.67.130 - - [22/Mar/2017:09:52:12 -0500] "GET / HTTP/1.1" 200 8081 "http://www.example.com/resources.php" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36"
    201.4.67.130 - - [22/Mar/2017:09:52:58 -0500] "GET /about.php HTTP/1.1" 200 4931 "http://www.example.com/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36"
    
Limitations
===========
Currently, only GET requests are supported, and only response codes of 200 (OK) or 404 (Page Not Found).
