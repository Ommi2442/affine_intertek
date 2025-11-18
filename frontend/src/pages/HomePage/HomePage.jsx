import React, { useState } from 'react';
import jsonData from '../../utils/new_ext_out.json'; // place your JSON file in src
import DataTable from '../../components/DataTable';
import LoginPage from '../LoginPage/LoginPage';
import BasicModal from '../../components/Modal';
import UploadFilePage from '../UploadFilePage/UploadFilePage';

function HomePage() {
  const [updatedData, setUpdatedData] = useState(jsonData);

  const handleDataChange = (newData) => {
    console.log('Updated JSON:', newData);
    setUpdatedData(newData);
  };

  return (
    <div>
      {/* <DataTable
        jsonData={jsonData}
        onDataChange={handleDataChange}
        report_name={'TRF'}
      /> */}

      {/* <LoginPage /> */}
    </div>
  );
}

export default HomePage;
