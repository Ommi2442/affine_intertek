import * as React from 'react';
import { Box, Button, Modal, TextField, Typography } from '@mui/material';

const style = {
  position: 'absolute',
  top: '50%',
  left: '50%',
  transform: 'translate(-50%, -50%)',
  width: 400,
  bgcolor: 'background.paper',
  borderRadius: '10px',
  boxShadow: 24,
  p: 4,
};

export default function BasicModal() {
  const [open, setOpen] = React.useState(false);
  const handleOpen = () => setOpen(true);
  const handleClose = () => setOpen(false);

  return (
    <>
      <Button variant="outlined" onClick={handleOpen}>
        Create Project
      </Button>

      <Modal open={open} onClose={handleClose}>
        <Box sx={style}>
          <Typography variant="h6" mb={2}>
            Create Project
          </Typography>

          <TextField fullWidth label="Standard" margin="normal" />
          <TextField fullWidth label="Client Name" margin="normal" />
          <TextField fullWidth label="Product" margin="normal" />
          <TextField fullWidth label="Project ID" margin="normal" />

          <Button
            variant="contained"
            fullWidth
            sx={{
              mt: 2,
              backgroundColor: 'black',
              '&:hover': { backgroundColor: '#333' },
            }}
          >
            Submit
          </Button>
        </Box>
      </Modal>
    </>
  );
}
