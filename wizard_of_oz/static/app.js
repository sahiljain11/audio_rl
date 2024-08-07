const UPLOAD_ENABLED = true
function uploadToS3(filename, file, isJSON) {
    if (UPLOAD_ENABLED) {
        let xhr = new XMLHttpRequest();

        xhr.open("GET", "/get_s3_url?filename="+filename);
        xhr.onreadystatechange = function(){
            if(xhr.readyState === 4){
                if(xhr.status === 200){
                    let response = JSON.parse(xhr.responseText);
                     uploadFile(file, response.data, response.url, response, isJSON);
                }
                else{
                    alert("Could not get signed URL.");
                }
            }
        };

        xhr.send();
    }
}

function uploadFile(file, s3Data, url, isJson){
    let xhr = new XMLHttpRequest();
    xhr.open("POST", s3Data.url);

    let postData = new FormData();
    for(let s3key in s3Data.fields){
        postData.append(s3key, s3Data.fields[s3key]);
    }

    if (isJson) {
        postData.append('file', JSON.stringify(file));
    } else {
        postData.append('file', file);
    }
    xhr.send(postData);
}

function uploadToServer(blob, filename, callback) {
    let xhr = new XMLHttpRequest();
    xhr.onload = function(e) {  // On success
      if(this.readyState === 4) {
          console.log("Server returned: ",e.target.responseText);
          callback();
      }
    };
    let fd = new FormData();
    fd.append("audio_data", blob, filename);
    fd.append("filename", filename)
    xhr.open("POST","/upload_file",true);
    xhr.send(fd);
    return xhr
}