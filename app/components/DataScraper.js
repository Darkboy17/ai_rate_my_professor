"use client"

import React, { useState } from 'react';
import axios from 'axios';
import { toast } from 'react-toastify';
import Toolbar from '@mui/material/Toolbar';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';


const DataScraper = () => {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);

    try {
      const url = document.querySelector('input[type="text"]').value.trim();

      if (!url) {
        toast.error("Please enter a URL.");
        return;
      }
  
      const response = await axios.get('http://localhost:5000/scrape', {
        params: { url }
      });

      const responseData = await response.data
      console.log("response status:", responseData)

      if (responseData.code === 100) {
        toast.success(responseData.message)
      } else if (responseData.code === 300) {
        toast.error(responseData.message)
      }
  
      
      setUrl('');
    } catch (error) {
        // Log the error and show a toast notification
        console.error('Error during request:', error);
        toast.error(`Request failed: ${error.message}`);
    } finally {
        // Always reset the loading state
        setLoading(false);
    }
};

  const handleInputChange = (e) => {
    setUrl(e.target.value);
  };

  return (
    <Toolbar>
      <form onSubmit={handleSubmit} style={{ display: 'flex', width: '100%' }}>
        <TextField
          label="Enter Professor's Page URL"
          variant="outlined"
          value={url}
          onChange={handleInputChange}
          required
          sx={{ width: '100%' }}
        />
        <Button
          type="submit"
          variant="contained"
          color="primary"
          disabled={loading || !url}
          style={{ marginLeft: 'auto' }}
        >
          {loading ? 'Processing...' : 'Scrape'}
        </Button>
      </form>
    </Toolbar>
  );
};

export default DataScraper;