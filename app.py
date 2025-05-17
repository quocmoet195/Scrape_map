import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from flask import Flask, render_template, request, session, flash, redirect
import time
from flask import jsonify
import json
import os

app = Flask(__name__)
app.secret_key="Quocmoet195"

def scroll_website(driver, count_cmt):
    i = 0
    new_height=0
    while True:
        try:
            body = driver.find_element(By.CLASS_NAME, 'm6QErb.DxyBCb.kA9KIf.dS8AEf.XiKgde')
            last_height=driver.execute_script("return arguments[0].scrollHeight", body)
            body.send_keys(Keys.PAGE_DOWN)
            time.sleep(0.4)  
            i += 1
            if not i%20:
                if last_height==new_height or i>count_cmt:
                    break
                last_height=new_height
                new_height = driver.execute_script("return arguments[0].scrollHeight", body)
                
        except Exception as e:
            print(f"Error during scrolling: {e}")
            break

def get_name(url):
    x = url.find("/maps/place/")
    y = url.find("/@13.")
    return url[x+12:y].replace("+"," ")

def extract_review(driver, url, count_cmt):
    data = []
    value_stars = []
    data.append({"name_url":get_name(url)})
    if count_cmt==0:
        try:
            average_star = driver.find_element(By.CLASS_NAME, "fontDisplayLarge").text
        except:
            average_star = 0

        try:
            stars = driver.find_elements(By.CLASS_NAME, "BHOKXe")
            star_labels = [star.get_attribute("aria-label") for star in stars]
            star_labels=[star_label.replace('\xa0','') for star_label in star_labels]
            print(star_labels)
            star_counts = {}
            for label in star_labels:
                x = re.findall(r"\d+", label)
                if len(x)==3:
                    x[1]=f"{x[1]},{x[2]}"
                if x:
                    rating = x[0]
                    count = x[1]
                    star_counts[rating] = count
            print(star_counts)
            value_stars = [[k + " ", v + " "] for k, v in star_counts.items()]
        except:
            value_stars = []

    else:       
        scroll_website(driver,count_cmt )
        reviewers = driver.find_elements(By.CLASS_NAME, "jftiEf.fontBodyMedium")
        try:
            average_star = driver.find_element(By.CLASS_NAME, "fontDisplayLarge").text
        except:
            average_star = 0

        try:
            stars = driver.find_elements(By.CLASS_NAME, "BHOKXe")
            star_labels = [star.get_attribute("aria-label") for star in stars]
            star_labels=[star_label.replace('\xa0','') for star_label in star_labels]
            print(star_labels)
            star_counts = {}
            for label in star_labels:
                x = re.findall(r"\d+", label)
                if len(x)==3:
                    x[1]=f"{x[1]},{x[2]}"
                if x:
                    rating = x[0]
                    count = x[1]
                    star_counts[rating] = count
            print(star_counts)
            value_stars = [[k + " ", v + " "] for k, v in star_counts.items()]
        except:
            value_stars = []

        for reviewer in reviewers[:count_cmt]:
            try:
                avatar_link = reviewer.find_element(By.CLASS_NAME, "NBa7we").get_attribute("src")
            except:
                avatar_link = None
            try:
                name_link = reviewer.find_element(By.CLASS_NAME, "d4r55").text
            except:
                name_link = None
            try:
                star = reviewer.find_element(By.CLASS_NAME, "kvMYJc").get_attribute("aria-label")[:1]
            except:
                star = 0
            try:
                time_of_review = reviewer.find_element(By.CLASS_NAME, "rsqaWe").text
            except:
                time_of_review = None
            try:
                comment = reviewer.find_element(By.CLASS_NAME, "wiI7pd").text.replace("\n", ".")
            except:
                comment = None
            try:
                image = reviewer.find_element(By.CLASS_NAME, "KtCyie")
                images = [img.get_attribute("style")[23:120] for img in image.find_elements(By.CLASS_NAME, "Tya61d")]
            except:
                images = []

            data.append({
                "avatar_link": avatar_link,
                "name_link": name_link,
                "star": star,
                "time_of_review": time_of_review,
                "comment": comment,
                "images": images
            })


    return data, average_star, value_stars


@app.route('/')
def index():
    return render_template('index.html')
data_store = {}
@app.route('/process', methods=['POST'])
def process():
    urls = request.form.getlist("urls") 
    count_cmt = int(request.form.get("count_cmt", 0))

    if not urls:
        return render_template('index.html', error="Please provide at least one URL.")

    results = []
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    # chrome_options.add_argument("--no-sandbox")
    # chrome_options.add_argument("--disable-dev-shm-usage")
    service = Service('C:\\Users\\ADMIN\\Downloads\\chromedriver-win64 (2)\\chromedriver-win64\\chromedriver.exe')
    for url in urls:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        #driver = webdriver.Chrome(executable_path='/usr/local/bin/chromedriver', options=chrome_options)
        driver.maximize_window()    
        try:
            driver.get(url)
            time.sleep(1)
            data, average_star, value_stars = extract_review(driver, url, count_cmt)

            results.append({"url": url, "data": data, "average_star": average_star, "value_stars": value_stars})
        except Exception as e:
            results.append({"url": url, "error": str(e)})
        finally:
            driver.quit()
        name=data[0].get('name_url')
        print(name)
        data_store[name] = data 
    return render_template('results.html', results=results)

@app.route('/save_reviewers', methods=['POST'])
def save_reviewers():
    for key in  data_store.keys():
        data=data_store.get(key)
        if not data:
            print("No data to save.") 
            flash("No data to save.", "error")  
        
        file_path = os.path.join(os.getcwd(), f"{key}.json")

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"Data saved successfully to {file_path}") 
            
        except Exception as e:
            print(f"Error saving data: {str(e)}")  
            flash(f"Error saving data: {str(e)}", "error")  
    
    return redirect('/')


if __name__ == "__main__":
    app.run(debug=True)