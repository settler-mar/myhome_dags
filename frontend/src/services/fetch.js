import useMessageStore from "@/store/messages";
import authStore from "@/store/auth";

function secureFetch(url, {
  method,
  data,
  body = null,
  dataType = 'json',
  headers,
  secure = true,
  files
} = {}) {
  const MessageStore = useMessageStore();
  data = data || body;

  headers = headers || {
    "Accept": "application/json",
  }

  if (!files) {
    headers["Content-Type"] = dataType === 'url' ? 'application/x-www-form-urlencoded' : "application/json; charset=utf-8"
  } else {
    dataType = 'multipart'
    let _data = new FormData();
    if (data) {
      for (const key in data) {
        if (data[key] instanceof File) {
          _data.append(key, data[key]);
        } else {
          _data.append(key, JSON.stringify(data[key]));
        }
      }
    }
    for (const key in files) {
      if (files[key] instanceof File) {
        _data.append(key, files[key]);
      } else {
        _data.append(key, JSON.stringify(files[key]));
      }
    }

    data = _data;
  }

  if (secure) {
    headers["Authorization"] = `Bearer ${localStorage.getItem("token")}`;
  }
  // new URLSearchParams(data) - dataType = 'url'
  // JSON.stringify(data) - dataType = 'json'
  // data - dataType = 'raw'
  if (data) {
    switch (dataType) {
      case 'url':
        body = new URLSearchParams(data);
        break;
      case 'json':
        body = JSON.stringify(data);
        break;
      default:
        body = data;
        break;
    }
  }
  // console.log('secureFetch', url, method, data, dataType, headers, body);
  return fetch(url, {
    method: method || "GET",
    body,
    mode: "cors",
    headers
  }).then(response => {
    // Server returned a status code of 2XX
    if (response.ok) {
      // you can call response.json() here if you want to return the json
      return response;
    }

    // Server returned a status code of 4XX or 5XX
    // Throw the response to handle it in the next catch block
    throw response;
  }).catch(async (error) => {
      const fallbackMessage = 'Some error occurred';
      let errorMessage = fallbackMessage;

      if (error instanceof Response) {
        try {
          const contentType = error.headers.get("Content-Type");
          if (contentType && contentType.includes("application/json")) {
            const errorData = await error.json();
            errorMessage = errorData?.error || errorData?.message || errorData?.detail || fallbackMessage;
          } else {
            errorMessage = await error.text();
          }
        } catch (e) {
          console.warn('Failed to parse error response', e);
        }

        switch (error.status) {
          case 400:
            errorMessage = errorMessage || 'Bad request';
            break;
          case 404:
            errorMessage = errorMessage || 'Object not found';
            break;
          case 500:
            errorMessage = errorMessage || 'Internal server error';
            break;
          case 401:
            errorMessage = errorMessage || 'Unauthorized';
            MessageStore.addMessage({type: "error", message: errorMessage});
            localStorage.setItem("redirect", location.pathname);
            const auth = authStore();
            auth.logout();
            location.href = '/login';
            throw error;
          default:
            break;
        }

        if (Array.isArray(errorMessage)) {
          for (const message of errorMessage) {
            if (message.type === 'missing') {
              MessageStore.addMessage({
                type: "error",
                message: `Missing field ${message.loc[1]}`,
              });
              continue;
            } else if (message.message || message.msg) {
              MessageStore.addMessage({
                type: "error",
                message: message.msg
              });
              continue;
            } else if (message.loc) {
              MessageStore.addMessage({
                type: "error",
                message: `Field ${message.loc[1] || message.type || message.loc[0]} ${message.msg || message.message}`,
              });
              continue;
            } else {
              MessageStore.addMessage({
                type: "error",
                message
              });
            }
          }
        } else {
          MessageStore.addMessage({
            type: "error",
            message: errorMessage,
          });
        }
      } else {
        // Handle network errors
        console.log('Network error');
        console.log(error);
        MessageStore.addMessage({
          type: "error",
          message: 'Network error',
        });
      }
      throw error;
    }
  )
    ;
}


// secureFetch('https://jsonplaceholder.typicode.com/posts/1')
//   .then(response => response.json())
//   .then(json => console.log(json))
//   .catch(error => console.log(error));
//
// secureFetch('https://jsonplaceholder.typicode.com/posts/100000000')
//   .then(response => response.json())
//   .then(json => console.log(json))
//   .catch(error => console.log(error));

export {secureFetch};
