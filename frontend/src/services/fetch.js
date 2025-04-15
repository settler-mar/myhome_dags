import useMessageStore from "@/store/messages";
import authStore from "@/store/auth";

function secureFetch(url, {method, data, body = null, dataType = 'json', headers, secure = true} = {}) {
  const MessageStore = useMessageStore();

  headers = headers || {
    "Accept": "application/json",
    "Content-Type": dataType === 'url' ? 'application/x-www-form-urlencoded' : "application/json; charset=utf-8"
  }

  if (secure) {
    headers["Authorization"] = `Bearer ${localStorage.getItem("token")}`;
  }
  // new URLSearchParams(data) - dataType = 'url'
  // JSON.stringify(data) - dataType = 'json'
  // data - dataType = 'raw'
  data = data || body;
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
  }).catch(error => {
    // It will be invoked for network errors and errors thrown from the then block
    // Do what ever you want to do with error here
    if (error instanceof Response) {
      // Handle error according to the status code
      switch (error.status) {
        case 404:
          // You can also call global notification service here
          // to show a notification to the user
          // notificationService.information('Object not found');
          console.log('Object not found');
          MessageStore.addMessage({
            type: "error",
            message: 'Object not found',
          });
          break;
        case 500:
          console.log('Internal server error');
          MessageStore.addMessage({
            type: "error",
            message: 'Internal server error',
          });
          break;
        case 401:
          console.log('Unauthorized');
          MessageStore.addMessage({
            type: "error",
            message: 'Unauthorized',
          });
          localStorage.setItem("redirect", location.pathname);

          const auth = authStore();
          auth.logout();
          location.href = '/login';
          break;
        default:
          console.log('Some error occurred');
          MessageStore.addMessage({
            type: "error",
            message: 'Some error occurred',
          });
          break;
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
  });
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
