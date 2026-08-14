export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:5000";


export async function apiRequest(
  path,
  options = {}
) {

  const response = await fetch(
    `${API_BASE_URL}${path}`,
    {

      ...options,

      credentials: "include",

      headers: {

        "Content-Type":
          "application/json",

        ...(options.headers || {}),
      },
    }
  );


  let data;


  try {

    data =
      await response.json();

  } catch {

    data = {

      success: false,

      error:
        "The server returned an invalid response.",
    };
  }


  if (!response.ok) {

    const error =
      new Error(
        data.error ||
        "The request could not be completed."
      );


    error.status =
      response.status;


    throw error;
  }


  return data;
}